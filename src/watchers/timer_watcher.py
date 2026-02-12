import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Dict

from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class TimerWatcher:
    """Genera eventos periódicos para monitorear tareas largas o recordatorios."""

    def __init__(self, bus: EventBus, interval: float = 60.0):
        self.bus = bus
        self.interval = interval
        self._running = False
        self._tick_count = 0

    async def run(self) -> None:
        self._running = True
        while self._running:
            await asyncio.sleep(self.interval)
            if not self._running:
                break
            self._tick_count += 1
            await self._publish_tick()

    def stop(self) -> None:
        self._running = False

    async def _publish_tick(self) -> None:
        message = LucyMessage(
            sender="timer_watcher",
            receiver="broadcast",
            type=MessageType.EVENT,
            content="timer_tick",
            data={"tick": self._tick_count, "interval": self.interval},
        )
        await self.bus.publish(message)
        self._log_event("timer_tick", {"tick": self._tick_count, "interval": self.interval})

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
