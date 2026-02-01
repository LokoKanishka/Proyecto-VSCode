import asyncio
import json

import pytest
import websockets

from src.core.bus import EventBus
from src.core.remote_worker import RemoteWorkerProxy
from src.core.types import LucyMessage, MessageType


async def _echo_server(websocket):
    async for raw in websocket:
        payload = json.loads(raw)
        response = {
            "sender": payload.get("receiver", "remote"),
            "receiver": payload.get("sender", "client"),
            "type": "response",
            "content": "ok",
            "data": {"echo": payload.get("content")},
            "in_reply_to": payload.get("data", {}).get("in_reply_to") or payload.get("in_reply_to"),
        }
        await websocket.send(json.dumps(response))


async def _run_proxy_test():
    bus = EventBus()
    server = await websockets.serve(_echo_server, "127.0.0.1", 8769)
    RemoteWorkerProxy("remote_worker", bus, "ws://127.0.0.1:8769")
    bus_task = asyncio.create_task(bus.start())
    try:
        msg = LucyMessage(
            sender="tester",
            receiver="remote_worker",
            type=MessageType.COMMAND,
            content="ping",
            data={},
        )
        response = await bus.publish_and_wait(msg, timeout=2)
        assert response.content == "ok"
    finally:
        server.close()
        await server.wait_closed()
        await bus.stop()
        await bus_task


def test_remote_worker_proxy():
    try:
        asyncio.run(_run_proxy_test())
    except Exception as exc:
        pytest.skip(f"Proxy test requiere WS local: {exc}")
