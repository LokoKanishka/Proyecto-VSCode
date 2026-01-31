import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class FileWatcher:
    """Monitorea directorios clave y publica eventos cuando aparecen o cambian archivos."""

    def __init__(
        self,
        bus: EventBus,
        directories: Optional[List[str]] = None,
        poll_interval: float = 6.0,
    ):
        self.bus = bus
        self.directories = [
            Path(p).expanduser() for p in (directories or ["~/Downloads", "~/Documentos"])
        ]
        self.poll_interval = poll_interval
        self._running = False
        self._state: Dict[str, Tuple[float, int]] = {}

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                snapshot = self._snapshot()
                for path, stats in snapshot.items():
                    if path not in self._state:
                        await self._publish_event("file_created", path, stats)
                    elif self._state[path] != stats:
                        await self._publish_event("file_modified", path, stats)
                self._state = snapshot
            except Exception as exc:
                logger.warning("FileWatcher falló: %s", exc)
            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self._running = False

    def _snapshot(self) -> Dict[str, Tuple[float, int]]:
        state: Dict[str, Tuple[float, int]] = {}
        for directory in self.directories:
            if not directory.exists():
                continue
            for path in directory.rglob("*"):
                if not path.is_file():
                    continue
                try:
                    stat = path.stat()
                    state[str(path)] = (stat.st_mtime, stat.st_size)
                except (OSError, PermissionError):
                    continue
        return state

    async def _publish_event(self, event_name: str, path: str, stats: Tuple[float, int]):
        message = LucyMessage(
            sender="file_watcher",
            receiver="broadcast",
            type=MessageType.EVENT,
            content="file_event",
            data={
                "event": event_name,
                "path": path,
                "timestamp": stats[0],
                "size": stats[1],
            },
        )
        await self.bus.publish(message)
        self._log_event(event_name, {"path": path, "size": stats[1]})

    def _log_event(self, event_name: str, data: Dict) -> None:
        record = {
            "timestamp": time.time(),
            "event": event_name,
            "data": data,
        }
        path = Path("logs/resource_events.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fd:
            fd.write(json.dumps(record) + "\n")
