import asyncio
import json
import logging
import os
import ssl
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
        self._clients: dict = {}
        self._subscribed_topics: set[str] = set()

    async def start(self) -> None:
        ssl_ctx = _build_ssl_context()
        self._server = await websockets.serve(self._handler, self.host, self.port, ssl=ssl_ctx)
        logger.info("WS Gateway escuchando en ws://%s:%d", self.host, self.port)

    async def stop(self) -> None:
        if self._server:
            self._server.close()
            await self._server.wait_closed()

    async def _handler(self, websocket):
        self._clients[websocket] = set()
        try:
            async for raw in websocket:
                try:
                    payload = json.loads(raw)
                    if _require_token(payload):
                        await websocket.send(json.dumps({"status": "error", "error": "unauthorized"}))
                        continue
                    action = payload.get("action")
                    if action == "subscribe":
                        topics = set(payload.get("topics", []))
                        self._clients[websocket] = topics
                        for topic in topics:
                            self._subscribe_topic(topic)
                        await websocket.send(json.dumps({"status": "ok", "subscribed": list(topics)}))
                        continue
                    if action == "publish":
                        message_payload = payload.get("message") or {}
                        msg = LucyMessage.model_validate(message_payload)
                    else:
                        msg = LucyMessage(
                            sender=payload.get("sender", "ws_client"),
                            receiver=payload.get("receiver", "broadcast"),
                            type=MessageType(payload.get("type", "event")),
                            content=payload.get("content", ""),
                            data=payload.get("data", {}),
                            in_reply_to=payload.get("in_reply_to"),
                        )
                    if payload.get("wait_response"):
                        response = await self.bus.publish_and_wait(msg, timeout=payload.get("timeout", 10))
                        await websocket.send(response.model_dump_json())
                    else:
                        await self.bus.publish(msg)
                        await websocket.send(json.dumps({"status": "ok"}))
                except Exception as exc:
                    await websocket.send(json.dumps({"status": "error", "error": str(exc)}))
        finally:
            self._clients.pop(websocket, None)

    def _subscribe_topic(self, topic: str) -> None:
        if topic in self._subscribed_topics:
            return
        self._subscribed_topics.add(topic)
        self.bus.subscribe(topic, self._forward_event)

    async def _forward_event(self, message: LucyMessage) -> None:
        if not self._clients:
            return
        payload = message.model_dump()
        dead = []
        for ws, topics in self._clients.items():
            if not topics or message.receiver in topics or (message.type == MessageType.EVENT and "broadcast" in topics):
                try:
                    await ws.send(json.dumps({"type": "event", "message": payload}))
                except Exception:
                    dead.append(ws)
        for ws in dead:
            self._clients.pop(ws, None)


def _require_token(payload: dict) -> bool:
    token = os.getenv("LUCY_WS_BRIDGE_TOKEN")
    if not token:
        return False
    return payload.get("token") != token


def _build_ssl_context() -> Optional[ssl.SSLContext]:
    cert = os.getenv("LUCY_WS_TLS_CERT")
    key = os.getenv("LUCY_WS_TLS_KEY")
    if not cert or not key:
        return None
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(certfile=cert, keyfile=key)
    return ctx
