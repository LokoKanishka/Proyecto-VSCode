import asyncio
import json
import logging
import shlex
import subprocess
import time
from pathlib import Path
from typing import Set

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class WindowWatcher:
    """Monitorea nuevas ventanas y publica eventos en el bus."""

    def __init__(self, bus: EventBus, poll_interval: float = 4.0):
        self.bus = bus
        self.poll_interval = poll_interval
        self._seen_windows: Set[str] = set()
        self._running = False

    async def run(self):
        self._running = True
        while self._running:
            try:
                current = self._list_windows()
                new_windows = current - self._seen_windows
                for win_id, title in new_windows:
                    logger.info("👁️ Nueva ventana detectada: %s (%s)", title, win_id)
                    await self.bus.publish(LucyMessage(
                        sender="window_watcher",
                        receiver="broadcast",
                        type=MessageType.EVENT,
                        content="window_opened",
                        data={"window_id": win_id, "title": title}
                    ))
                    self._log_event("window_opened", {"window_id": win_id, "title": title})
                self._seen_windows.update(current)
            except Exception as exc:
                logger.debug("Falló WindowWatcher: %s", exc)
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        self._running = False

    def _list_windows(self):
        try:
            output = subprocess.check_output(["wmctrl", "-l"], text=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            return set()
        windows = set()
        for line in output.splitlines():
            parts = shlex.split(line, posix=False)
            if len(parts) < 4:
                continue
            win_id = parts[0]
            title = " ".join(parts[3:])
            windows.add((win_id, title))
        return windows

    def _log_event(self, event_name: str, data: dict) -> None:
        record = {
            "timestamp": time.time(),
            "event": event_name,
            "data": data
        }
        path = Path("logs/resource_events.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fd:
            fd.write(json.dumps(record) + "\n")
