import asyncio
import logging
import os

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType, WorkerType

logger = logging.getLogger(__name__)


class MemoryBackupWatcher:
    """Dispara backups periódicos de memoria vía MemoryWorker."""

    def __init__(self, bus: EventBus, interval_s: int = 3600):
        self.bus = bus
        self.interval_s = interval_s
        self._running = True

    async def run(self) -> None:
        while self._running:
            await asyncio.sleep(self.interval_s)
            await self._request_backup()

    def stop(self) -> None:
        self._running = False

    async def _request_backup(self) -> None:
        require_enc = os.getenv("LUCY_BACKUP_REQUIRE_ENCRYPTION", "0") in {"1", "true", "yes"}
        if require_enc and not os.getenv("LUCY_BACKUP_PASSPHRASE"):
            logger.warning("Backup omitido: falta LUCY_BACKUP_PASSPHRASE con cifrado obligatorio.")
            return
        logger.info("🧠 Backup de memoria programado.")
        msg = LucyMessage(
            sender="memory_backup_watcher",
            receiver=WorkerType.MEMORY,
            type=MessageType.COMMAND,
            content="backup_memory",
            data={"trigger": "watcher"},
        )
        await self.bus.publish(msg)
