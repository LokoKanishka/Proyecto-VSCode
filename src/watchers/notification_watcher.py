import asyncio
import json
import logging
import shutil
import time
from pathlib import Path
from typing import Dict, Optional

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class NotificationWatcher:
    """Escucha notificaciones del bus de D-Bus y publica eventos al enjambre."""

    def __init__(self, bus: EventBus):
        self.bus = bus
        self._running = False
        self._process: Optional[asyncio.subprocess.Process] = None

    async def run(self) -> None:
        self._running = True
        monitor_cmd = shutil.which("dbus-monitor")
        if not monitor_cmd:
            await self._stub_loop()
            return

        try:
            self._process = await asyncio.create_subprocess_exec(
                monitor_cmd,
                "--session",
                "interface='org.freedesktop.Notifications'",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await self._read_notifications()
        except Exception as exc:
            logger.warning("NotificationWatcher no pudo arrancar: %s", exc)
        finally:
            self.stop()

    async def _read_notifications(self) -> None:
        assert self._process
        buffer = []
        while self._running:
            line = await self._process.stdout.readline()
            if not line:
                break
            decoded = line.decode(errors="ignore").strip()
            buffer.append(decoded)
            if "member=Notify" in decoded:
                detail = self._parse_notification(buffer[-6:])
                await self._emit_event(detail)
                buffer = []

    def stop(self) -> None:
        self._running = False
        if self._process and self._process.returncode is None:
            self._process.terminate()

    async def _stub_loop(self) -> None:
        logger.info("NotificationWatcher sin dbus-monitor; emito ticks de prueba.")
        while self._running:
            await asyncio.sleep(15)
            await self._emit_event({"note": "monitor no disponible"})

    async def _emit_event(self, details: Dict) -> None:
        message = LucyMessage(
            sender="notification_watcher",
            receiver="broadcast",
            type=MessageType.EVENT,
            content="notification_received",
            data=details,
        )
        await self.bus.publish(message)
        self._log_event("notification_received", details)

    def _parse_notification(self, lines: list[str]) -> Dict:
        payload = {"raw": lines}
        for line in lines:
            if "string" in line:
                payload.setdefault("strings", []).append(line)
        return payload

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
