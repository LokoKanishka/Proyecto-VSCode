import asyncio
import json
import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class ResourceWatcher:
    """Monitorea uso de GPU y RAM para disparar eventos si se acerca al límite."""

    NVSMI_PATTERN = re.compile(r"(\d+),\s*(\d+)")

    def __init__(self, bus: EventBus, poll_interval: float = 5.0, gpu_threshold: float = 0.85):
        self.bus = bus
        self.poll_interval = poll_interval
        self.gpu_threshold = gpu_threshold
        self._running = False

    async def run(self):
        self._running = True
        while self._running:
            try:
                usage = self._query_gpu()
                if usage and usage >= self.gpu_threshold:
                    await self.bus.publish(LucyMessage(
                        sender="resource_watcher",
                        receiver="broadcast",
                        type=MessageType.EVENT,
                        content="gpu_pressure",
                        data={"usage_pct": usage}
                    ))
                    self._log_event("gpu_pressure", {"usage_pct": usage})
            except Exception as exc:
                logger.debug("ResourceWatcher falló: %s", exc)
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        self._running = False

    def _query_gpu(self) -> Optional[float]:
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                stderr=subprocess.DEVNULL
            ).strip().splitlines()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
        max_usage = 0.0
        for line in output:
            match = self.NVSMI_PATTERN.search(line)
            if not match:
                continue
            used = float(match.group(1))
            total = float(match.group(2))
            if total <= 0:
                continue
            max_usage = max(max_usage, used / total)
        return max_usage or None

    def _log_event(self, event_name: str, data: Dict):
        from pathlib import Path
        record = {
            "timestamp": time.time(),
            "event": event_name,
            "data": data
        }
        path = Path("logs/resource_events.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fd:
            fd.write(json.dumps(record) + "\n")
