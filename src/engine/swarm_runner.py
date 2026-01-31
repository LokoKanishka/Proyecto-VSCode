import asyncio
import logging
import signal
from typing import List, Optional

from src.core.bus import EventBus
from src.core.types import WorkerType
from src.memory.memory_manager import MemoryManager
from src.resources.resource_manager import ResourceManager
from src.watchers.file_watcher import FileWatcher
from src.watchers.notification_watcher import NotificationWatcher
from src.watchers.resource_watcher import ResourceWatcher
from src.watchers.timer_watcher import TimerWatcher
from src.watchers.window_watcher import WindowWatcher
from src.workers.browser_worker import BrowserWorker
from src.workers.chat_worker import ChatWorker
from src.workers.code_worker import CodeWorker
from src.workers.hands_worker import HandsWorker
from src.workers.search_worker import SearchWorker
from src.workers.vision_worker import VisionWorker
from src.core.manager import Manager

logger = logging.getLogger(__name__)


class SwarmRunner:
    """Arranca el enjambre completo y lo mantiene vivo hasta recibir SIGINT/SIGTERM."""

    def __init__(self, memory_db: str = "lucy_memory.db"):
        self.bus = EventBus()
        self.memory = MemoryManager(db_path=memory_db)
        self.manager = Manager(self.bus, self.memory)
        self.workers = [
            SearchWorker(WorkerType.SEARCH, self.bus),
            ChatWorker(WorkerType.CHAT, self.bus),
            CodeWorker(WorkerType.CODE, self.bus),
            VisionWorker(WorkerType.VISION, self.bus),
            BrowserWorker(WorkerType.BROWSER, self.bus),
            HandsWorker(WorkerType.HANDS, self.bus),
        ]
        self.resource_manager = ResourceManager()
        self.watchers = [
            ResourceWatcher(self.bus),
            WindowWatcher(self.bus),
            FileWatcher(self.bus),
            NotificationWatcher(self.bus),
            TimerWatcher(self.bus, interval=60.0),
        ]
        self.watcher_tasks: List[asyncio.Task] = []
        self.bus_task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

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
        logger.info("🤖 Swarm en marcha. Presioná Ctrl+C para detener.")
        await self._stop_event.wait()
        await self.stop()

    def _start_watchers(self) -> None:
        self.watcher_tasks = [
            asyncio.create_task(watcher.run()) for watcher in self.watchers
        ]

    async def stop(self) -> None:
        """Detiene watchers, el bus y limpia el entorno."""
        logger.info("🛑 Deteniendo Swarm Runner...")
        for watcher in self.watchers:
            watcher.stop()
        for task in self.watcher_tasks:
            task.cancel()
        await asyncio.gather(*self.watcher_tasks, return_exceptions=True)
        if self.bus_task:
            await self.bus.stop()
            await self.bus_task
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
