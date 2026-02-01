import asyncio
import json
import logging
from typing import Optional

import websockets

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class WebSocketGateway:
    """
    Gateway WS simple para publicar mensajes al bus y devolver respuestas.
    """

    def __init__(self, bus: EventBus, host: str = "127.0.0.1", port: int = 8766):
        self.bus = bus
        self.host = host
        self.port = port
        self._server: Optional[websockets.server.Serve] = None

    async def start(self) -> None:
        self._server = await websockets.serve(self._handler, self.host, self.port)
        logger.info("WS Gateway escuchando en ws://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handler(self, websocket):
        async for raw in websocket:
            try:
                payload = json.loads(raw)
                msg = LucyMessage(
                    sender=payload.get("sender", "ws_client"),
                    receiver=payload.get("receiver", "broadcast"),
                    type=MessageType(payload.get("type", "event")),
                    content=payload.get("content", ""),
                    data=payload.get("data", {}),
                )
                if payload.get("wait_response"):
                    response = await self.bus.publish_and_wait(msg, timeout=payload.get("timeout", 10))
                    await websocket.send(response.model_dump_json())
                else:
                    await self.bus.publish(msg)
                    await websocket.send(json.dumps({"status": "ok"}))
            except Exception as exc:
                await websocket.send(json.dumps({"status": "error", "error": str(exc)}))
