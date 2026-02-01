import asyncio
import logging
import os
import signal
from typing import List, Optional

from src.core.bus import EventBus
from src.core.types import WorkerType
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
from src.workers.browser_worker import BrowserWorker
from src.workers.chat_worker import ChatWorker
from src.workers.code_worker import CodeWorker
from src.workers.hands_worker import HandsWorker
from src.workers.memory_worker import MemoryWorker
from src.workers.search_worker import SearchWorker
from src.workers.shell_worker import ShellWorker
from src.workers.vscode_worker import VSCodeWorker
from src.workers.git_worker import GitWorker
from src.workers.package_worker import PackageWorker
from src.workers.vision_worker import VisionWorker
from src.workers.ear_worker import EarWorker
from src.workers.mouth_worker import MouthWorker
from src.core.manager import Manager
from src.engine.swarm_manager import SwarmManager
from src.planners.ollama_planner import OllamaPlanner
from src.planners.tree_of_thought_llm import TreeOfThoughtLLMPlanner
from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.audio import AudioCaptureGate
from src.core.ws_gateway import WebSocketGateway
from src.core.remote_worker import RemoteWorkerProxy

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
        self.ws_gateway: Optional[WebSocketGateway] = None
        self._stop_event = asyncio.Event()
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
        """Ejecuta el bus y los watchers hasta que el usuario interrumpe con Ctrl+C."""
        logger.info("⚙️ Iniciando Swarm Runner...")
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, self._request_stop)
            except NotImplementedError:
                # Windows event loop no soporta add_signal_handler con asyncio
                pass

        self.bus_task = asyncio.create_task(self.bus.start())
        self._start_watchers()
        self._start_audio()
        await self._start_ws_gateway()
        logger.info("🤖 Swarm en marcha. Presioná Ctrl+C para detener.")
        await self._stop_event.wait()
        await self.stop()

    def _start_watchers(self) -> None:
        self.watcher_tasks = [
            asyncio.create_task(watcher.run()) for watcher in self.watchers
        ]

    def _start_audio(self) -> None:
        if getattr(self, "ear_worker", None):
            self.audio_tasks.append(asyncio.create_task(self.ear_worker.run()))

    async def _start_ws_gateway(self) -> None:
        if os.getenv("LUCY_WS_GATEWAY", "0").lower() in {"1", "true", "yes"}:
            host = os.getenv("LUCY_WS_HOST", "127.0.0.1")
            port = int(os.getenv("LUCY_WS_PORT", "8766"))
            self.ws_gateway = WebSocketGateway(self.bus, host=host, port=port)
            await self.ws_gateway.start()

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
        if self.bus_task:
            await self.bus.stop()
            await self.bus_task
        if self.ws_gateway:
            await self.ws_gateway.stop()
        logger.info("✅ Swarm detenido.")

    def _request_stop(self) -> None:
        if not self._stop_event.is_set():
            logger.info("📩 Señal recibida, preparando apagado...")
            self._stop_event.set()


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
