import asyncio
import json
import logging
import os
from datetime import datetime

from src.core.bus import EventBus
from src.core.lucy_types import MessageType

logger = logging.getLogger(__name__)


class BusMetricsWatcher:
    """Registra métricas periódicas del EventBus y las escribe en disco."""

    def __init__(self, bus: EventBus, log_path: str = "logs/bus_metrics.jsonl", interval: float = 5.0):
        self.bus = bus
        self.log_path = log_path
        self.interval = interval
        self._running = True
        self._bridge_stats = {}
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        self.bus.subscribe("broadcast", self.handle_event)

    async def handle_event(self, message):
        if message.type != MessageType.EVENT:
            return
        if message.content != "bridge_stats":
            return
        self._bridge_stats = message.data or {}

    async def run(self) -> None:
        while self._running:
            metrics = self.bus.get_metrics()
            latency = self.bus.get_latency_metrics()
            record = {
                "timestamp": datetime.now().isoformat(),
                "metrics": metrics,
                "bridge": self._bridge_stats,
                "latency": latency,
            }
            try:
                with open(self.log_path, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(record) + "\n")
            except OSError as exc:
                logger.warning("No se pudo escribir métricas del bus: %s", exc)
            await asyncio.sleep(self.interval)

    def stop(self) -> None:
        self._running = False
