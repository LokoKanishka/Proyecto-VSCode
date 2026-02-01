import asyncio
import json
import logging
from typing import Optional

import websockets

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class RemoteWorkerProxy:
    """
    Proxy que reenvía mensajes del bus a un worker remoto vía WebSocket.
    """

    def __init__(self, worker_id: str, bus: EventBus, url: str):
        self.worker_id = worker_id
        self.bus = bus
        self.url = url
        self.bus.subscribe(worker_id, self.handle_message)

    async def handle_message(self, message: LucyMessage):
        payload = {
            "sender": message.sender,
            "receiver": message.receiver,
            "type": message.type.value,
            "content": message.content,
            "data": {**message.data, "in_reply_to": message.id},
            "in_reply_to": message.in_reply_to,
            "wait_response": True,
        }
        try:
            response = await self._send(payload)
            if response.get("status") == "error":
                await self._publish_error(message, response.get("error", "remote_error"))
                return
            try:
                msg = LucyMessage.model_validate(response)
            except Exception:
                msg = LucyMessage(
                    sender=self.worker_id,
                    receiver=message.sender,
                    type=MessageType.RESPONSE,
                    content=str(response),
                    in_reply_to=message.id,
                )
            await self.bus.publish(msg)
        except Exception as exc:
            await self._publish_error(message, str(exc))

    async def _send(self, payload: dict) -> dict:
        async with websockets.connect(self.url) as ws:
            await ws.send(json.dumps(payload))
            raw = await ws.recv()
            try:
                return json.loads(raw)
            except Exception:
                return {"status": "error", "error": "invalid_json"}

    async def _publish_error(self, message: LucyMessage, error: str) -> None:
        await self.bus.publish(
            LucyMessage(
                sender=self.worker_id,
                receiver=message.sender,
                type=MessageType.ERROR,
                content=error,
                in_reply_to=message.id,
            )
        )
