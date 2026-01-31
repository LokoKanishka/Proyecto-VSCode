import asyncio
import logging
import os
from datetime import datetime

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class MemoryWatcher:
    """Registra eventos de contexto recuperado para monitorear su uso."""

    def __init__(self, bus: EventBus, log_path: str = "logs/memory_retrieval.log", interval: float = 5.0):
        self.bus = bus
        self.log_path = log_path
        self.interval = interval
        self._running = True
        self._count = 0
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        bus.subscribe("retrieved_memory", self._on_memory_event)

    async def run(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        self._running = False

    async def _on_memory_event(self, message: LucyMessage) -> None:
        if message.type != MessageType.EVENT:
            return

        self._count += 1
        context = message.data.get("context", [])
        summary = f"{datetime.now().isoformat()} | retrieved_memory #{self._count}: {len(context)} items\n"
        logger.info(summary.strip())
        try:
            with open(self.log_path, "a", encoding="utf-8") as fh:
                fh.write(summary)
        except OSError as exc:
            logger.warning("No pude registrar el evento de memoria: %s", exc)
