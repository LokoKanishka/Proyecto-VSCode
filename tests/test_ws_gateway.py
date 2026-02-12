import asyncio
import json
import websockets

from src.core.bus import EventBus
from src.core.ws_gateway import WebSocketGateway
from src.core.lucy_types import LucyMessage, MessageType


async def _run_gateway_test():
    bus = EventBus()
    gateway = WebSocketGateway(bus, host="127.0.0.1", port=8767)
    bus_task = asyncio.create_task(bus.start())
    await gateway.start()

    try:
        async with websockets.connect("ws://127.0.0.1:8767") as ws:
            payload = {
                "sender": "test_client",
                "receiver": "broadcast",
                "type": "event",
                "content": "ping",
                "data": {"x": 1},
            }
            await ws.send(json.dumps(payload))
            raw = await ws.recv()
            data = json.loads(raw)
            assert data["status"] == "ok"
    finally:
        await gateway.stop()
        await bus.stop()
        await bus_task


def test_ws_gateway_basic():
    asyncio.run(_run_gateway_test())
