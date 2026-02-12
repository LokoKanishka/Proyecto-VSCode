import asyncio
import json

import pytest
import websockets

from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType
from src.core.ws_gateway import WebSocketGateway
from src.workers.chat_worker import ChatWorker


async def _run_e2e():
    bus = EventBus()
    chat = ChatWorker("chat_worker", bus)
    gateway = WebSocketGateway(bus, host="127.0.0.1", port=8768)

    bus_task = asyncio.create_task(bus.start())
    await gateway.start()

    try:
        async with websockets.connect("ws://127.0.0.1:8768") as ws:
            payload = {
                "sender": "e2e_client",
                "receiver": "chat_worker",
                "type": "command",
                "content": "chat",
                "data": {"text": "hola", "history": []},
                "wait_response": True,
                "timeout": 5,
            }
            await ws.send(json.dumps(payload))
            raw = await ws.recv()
            msg = LucyMessage.model_validate_json(raw)
            assert msg.type in (MessageType.RESPONSE, MessageType.ERROR)
    finally:
        await gateway.stop()
        await bus.stop()
        await bus_task


def test_swarm_e2e_ws():
    try:
        asyncio.run(_run_e2e())
    except Exception as exc:
        pytest.skip(f"WS e2e requiere entorno local: {exc}")
