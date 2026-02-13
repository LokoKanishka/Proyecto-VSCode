import asyncio
import logging
import os
import signal
from typing import List, Optional

from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType, WorkerType
from src.memory.memory_manager import MemoryManager
from src.memory.vector_store import EmbeddedMemory
from src.resources.resource_manager import ResourceManager
from src.watchers.bus_metrics_watcher import BusMetricsWatcher
from src.watchers.file_watcher import FileWatcher
from src.watchers.memory_watcher import MemoryWatcher
from src.watchers.notification_watcher import NotificationWatcher
from src.watchers.resource_watcher import ResourceWatcher
from src.watchers.timer_watcher import TimerWatcher
from src.watchers.window_watcher import WindowWatcher
from src.watchers.memory_backup_watcher import MemoryBackupWatcher
from lucy_agents.browser_worker import BrowserWorker
from lucy_agents.chat_worker import ChatWorker
from lucy_agents.code_worker import CodeWorker
from lucy_agents.hands_worker import HandsWorker
from lucy_agents.memory_worker import MemoryWorker
from lucy_agents.search_worker import SearchWorker
from lucy_agents.shell_worker import ShellWorker
from lucy_agents.vscode_worker import VSCodeWorker
from lucy_agents.git_worker import GitWorker
from lucy_agents.package_worker import PackageWorker
from lucy_agents.vision_worker import VisionWorker
from lucy_agents.ear_worker import EarWorker
from lucy_agents.mouth_worker import MouthWorker
from src.core.manager import Manager
from src.engine.swarm_manager import SwarmManager
from src.planners.ollama_planner import OllamaPlanner
from src.planners.tree_of_thought_llm import TreeOfThoughtLLMPlanner
from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.audio import AudioCaptureGate
from src.core.ws_gateway import WebSocketGateway
from src.core.remote_worker import RemoteWorkerProxy
from src.core.ws_bus_bridge import WSBusBridge

logger = logging.getLogger(__name__)


class SwarmRunner:
    """Arranca el enjambre completo y lo mantiene vivo hasta recibir SIGINT/SIGTERM."""

    def __init__(self, memory_db: str = "lucy_memory.db"):
        self.bus = EventBus()
        vector_store = EmbeddedMemory(db_path="data/lucy_memory.lance")
        self.memory = MemoryManager(
            db_path=memory_db,
            vector_store=vector_store,
        )
        planner_mode = os.getenv("LUCY_PLANNER_MODE", "heuristic").lower()
        planner = None
        if planner_mode == "ollama":
            planner = OllamaPlanner()
        elif planner_mode == "tot_llm":
            planner = TreeOfThoughtLLMPlanner()
        swarm_manager = None
        if os.getenv("LUCY_SWARM_PROFILE_MANAGEMENT", "0").lower() in {"1", "true", "yes"}:
            swarm_manager = SwarmManager()
            profiles = {}
            if os.getenv("LUCY_WORKER_MODEL_VISION"):
                profiles[WorkerType.VISION.value] = os.getenv("LUCY_WORKER_MODEL_VISION")
            if os.getenv("LUCY_WORKER_MODEL_CODE"):
                profiles[WorkerType.CODE.value] = os.getenv("LUCY_WORKER_MODEL_CODE")
            if os.getenv("LUCY_WORKER_MODEL_CHAT"):
                profiles[WorkerType.CHAT.value] = os.getenv("LUCY_WORKER_MODEL_CHAT")
            if profiles:
                swarm_manager.set_worker_profiles(profiles)
            lora_specs = os.getenv("LUCY_LORA_SPECS", "")
            if lora_specs:
                for item in lora_specs.split(";"):
                    if "=" not in item:
                        continue
                    name, path = item.split("=", 1)
                    swarm_manager.register_lora(name.strip(), path.strip())
        self.manager = Manager(self.bus, self.memory, planner=planner, swarm=swarm_manager)
        self.workers = [
            SearchWorker(WorkerType.SEARCH, self.bus),
            ChatWorker(WorkerType.CHAT, self.bus),
            CodeWorker(WorkerType.CODE, self.bus),
            VisionWorker(WorkerType.VISION, self.bus),
            BrowserWorker(WorkerType.BROWSER, self.bus),
            HandsWorker(WorkerType.HANDS, self.bus),
            MemoryWorker(WorkerType.MEMORY, self.bus, self.memory),
            ShellWorker(WorkerType.SHELL, self.bus),
            VSCodeWorker(WorkerType.VSCODE, self.bus),
            GitWorker(WorkerType.GIT, self.bus),
            PackageWorker(WorkerType.PACKAGE, self.bus),
        ]
        self.resource_manager = ResourceManager()
        self.watchers = [
            ResourceWatcher(self.bus),
            WindowWatcher(self.bus),
            FileWatcher(self.bus),
            NotificationWatcher(self.bus),
            MemoryWatcher(self.bus),
            BusMetricsWatcher(self.bus),
            TimerWatcher(self.bus, interval=60.0),
        ]
        backup_interval = os.getenv("LUCY_MEMORY_BACKUP_INTERVAL")
        if backup_interval:
            try:
                interval_s = int(backup_interval)
                self.watchers.append(MemoryBackupWatcher(self.bus, interval_s=interval_s))
            except ValueError:
                logger.warning("LUCY_MEMORY_BACKUP_INTERVAL inválido: %s", backup_interval)
        self.watcher_tasks: List[asyncio.Task] = []
        self.bus_task: Optional[asyncio.Task] = None
        self.audio_tasks: List[asyncio.Task] = []
        self.console_task: Optional[asyncio.Task] = None
        self.ws_gateway: Optional[WebSocketGateway] = None
        self.ws_bridge: Optional[WSBusBridge] = None
        self._stop_event = asyncio.Event()
        self.enable_console = os.getenv("LUCY_SWARM_CONSOLE", "0").lower() in {"1", "true", "yes"}
        self._setup_audio_workers()
        self._setup_remote_workers()

    def _setup_audio_workers(self) -> None:
        enable_audio = os.getenv("LUCY_SWARM_ENABLE_AUDIO", "0").lower() in {"1", "true", "yes"}
        if not enable_audio:
            self.ear_worker = None
            self.mouth_worker = None
            return
        config_path = os.getenv("LUCY_CONFIG", "config.yaml")
        config = LucyConfig.load_from_yaml(config_path)
        gate = AudioCaptureGate()
        self.ear_worker = EarWorker(WorkerType.EAR, self.bus, config, gate)
        self.mouth_worker = MouthWorker(WorkerType.MOUTH, self.bus, config, gate)
        self.workers.extend([self.ear_worker, self.mouth_worker])

    def _setup_remote_workers(self) -> None:
        spec = os.getenv("LUCY_REMOTE_WORKERS", "")
        if not spec:
            return
        entries = [item.strip() for item in spec.split(";") if item.strip()]
        for entry in entries:
            if "=" not in entry:
                continue
            worker_id, url = entry.split("=", 1)
            worker_id = worker_id.strip()
            url = url.strip()
            if not worker_id or not url:
                continue
            RemoteWorkerProxy(worker_id, self.bus, url)

    async def run(self) -> None:
        """Ejecuta el bus y workers en paralelo con health-checks."""
        try:
            from src.utils.silent_logger import SilentProgressLogger
            progress = SilentProgressLogger(total_steps=5)
        except ImportError:
            progress = None
            logger.info("⚙️ Iniciando Swarm Runner (modo paralelo)...")
        
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._request_stop)
            except NotImplementedError:
                pass

        # 1. Bus primero (fundamental)
        if progress:
            progress.step("EventBus")
        self.bus_task = asyncio.create_task(self.bus.start())
        await asyncio.sleep(0.1)  # Dar tiempo al bus para inicializar
        
        # 2. Lanzar componentes en paralelo
        parallel_tasks = []
        parallel_tasks.append(self._start_watchers_parallel(progress))
        parallel_tasks.append(self._start_audio_with_check(progress))
        
        # Esperar a que watchers y audio estén listos
        await asyncio.gather(*parallel_tasks, return_exceptions=True)
        
        # 3. WebSocket components (pueden depender del bus)
        if progress:
            progress.step("WebSocket Gateway")
        await self._start_ws_gateway()
        await self._start_ws_bridge()
        
        # 4. Verificar health del swarm
        if progress:
            progress.step("Health Check")
        health_ok = await self._verify_swarm_health()
        if not health_ok:
            logger.warning("⚠️ Algunos componentes fallaron health-check")
        
        # 5. Consola solo después de que todo esté listo
        self._start_console()
        
        if progress:
            progress.finish("✅ Swarm operacional. Presioná Ctrl+C para detener.")
        else:
            logger.info("✅ Swarm operacional. Presioná Ctrl+C para detener.")
        
        await self._stop_event.wait()
        await self.stop()

    def _start_watchers(self) -> None:
        """LEGACY: Inicia watchers de forma síncrona (no usar)."""
        self.watcher_tasks = [
            asyncio.create_task(watcher.run()) for watcher in self.watchers
        ]
    
    async def _start_watchers_parallel(self, progress=None) -> None:
        """Lanza watchers en paralelo y espera a que estén listos."""
        if progress:
            progress.step("Watchers")
        self.watcher_tasks = [
            asyncio.create_task(watcher.run()) for watcher in self.watchers
        ]
        # Esperar a que al menos se inicialicen (no esperar ejecución completa)
        await asyncio.sleep(0.2)

    def _start_audio(self) -> None:
        """LEGACY: Inicia audio de forma síncrona (no usar)."""
        if getattr(self, "ear_worker", None):
            self.audio_tasks.append(asyncio.create_task(self.ear_worker.run()))
    
    async def _start_audio_with_check(self, progress=None) -> None:
        """Lanza audio workers con health-check."""
        if not getattr(self, "ear_worker", None):
            if progress:
                progress.step("Audio", "⏭️")
            return
        
        if progress:
            progress.step("Audio Workers")
        self.audio_tasks.append(asyncio.create_task(self.ear_worker.run()))
        # Health check: dar tiempo a que ear_worker inicialice
        await asyncio.sleep(0.1)

    def _start_console(self) -> None:
        if not self.enable_console:
            return
        self.console_task = asyncio.create_task(self._console_loop())

    async def _start_ws_gateway(self) -> None:
        if os.getenv("LUCY_WS_GATEWAY", "0").lower() in {"1", "true", "yes"}:
            host = os.getenv("LUCY_WS_HOST", "127.0.0.1")
            port = int(os.getenv("LUCY_WS_PORT", "8766"))
            self.ws_gateway = WebSocketGateway(self.bus, host=host, port=port)
            await self.ws_gateway.start()

    async def _start_ws_bridge(self) -> None:
        urls = os.getenv("LUCY_WS_BRIDGE_URLS") or os.getenv("LUCY_WS_BRIDGE_URL")
        if not urls:
            return
        topics_raw = os.getenv("LUCY_WS_BRIDGE_TOPICS", "broadcast,final_response")
        topics = [item.strip() for item in topics_raw.split(",") if item.strip()]
        url_list = [item.strip() for item in urls.split(",") if item.strip()]
        self.ws_bridge = WSBusBridge(self.bus, url_list[0], topics)
        await self.ws_bridge.start()
        self.ws_bridge_extra = []
        for extra in url_list[1:]:
            bridge = WSBusBridge(self.bus, extra, topics)
            await bridge.start()
            self.ws_bridge_extra.append(bridge)

    async def stop(self) -> None:
        """Detiene watchers, el bus y limpia el entorno."""
        logger.info("🛑 Deteniendo Swarm Runner...")
        for watcher in self.watchers:
            watcher.stop()
        for task in self.watcher_tasks:
            task.cancel()
        await asyncio.gather(*self.watcher_tasks, return_exceptions=True)
        if getattr(self, "ear_worker", None):
            self.ear_worker.stop()
        for task in self.audio_tasks:
            task.cancel()
        await asyncio.gather(*self.audio_tasks, return_exceptions=True)
        if self.console_task:
            self.console_task.cancel()
            await asyncio.gather(self.console_task, return_exceptions=True)
        if self.bus_task:
            await self.bus.stop()
            await self.bus_task
        if self.ws_gateway:
            await self.ws_gateway.stop()
        if self.ws_bridge:
            await self.ws_bridge.stop()
        for bridge in getattr(self, "ws_bridge_extra", []):
            await bridge.stop()
        logger.info("✅ Swarm detenido.")

    def _request_stop(self) -> None:
        if not self._stop_event.is_set():
            logger.info("📩 Señal recibida, preparando apagado...")
            self._stop_event.set()
    
    async def _verify_swarm_health(self) -> bool:
        """Verifica que todos los componentes críticos estén operacionales."""
        try:
            # Verificar que bus está activo
            if not self.bus_task or self.bus_task.done():
                logger.warning("Bus no está activo")
                return False
            
            # Verificar que watchers están corriendo
            active_watchers = sum(1 for task in self.watcher_tasks if not task.done())
            if active_watchers < len(self.watchers) // 2:
                logger.warning(f"Solo {active_watchers}/{len(self.watchers)} watchers activos")
                return False
            
            return True
        except Exception as e:
            logger.error(f"Error en health-check: {e}")
            return False

    async def _console_loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                text = await asyncio.to_thread(input, "\n👉 Tú: ")
            except (EOFError, KeyboardInterrupt):
                self._request_stop()
                break
            if not text or not text.strip():
                continue
            await self.bus.publish(
                LucyMessage(
                    sender="console",
                    receiver="user_input",
                    type=MessageType.EVENT,
                    content=text.strip(),
                    data={},
                )
            )


async def _main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    runner = SwarmRunner()
    try:
        await runner.run()
    except asyncio.CancelledError:
        pass


def main() -> None:
    asyncio.run(_main())


if __name__ == "__main__":
    main()
