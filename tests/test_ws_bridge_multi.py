import asyncio
import pytest

from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType
from src.core.ws_gateway import WebSocketGateway
from src.core.ws_bus_bridge import WSBusBridge


@pytest.mark.asyncio
async def test_ws_bridge_multi_node_event():
    bus_a = EventBus()
    bus_b = EventBus()
    gateway = WebSocketGateway(bus_a, host="127.0.0.1", port=8769)
    await gateway.start()
    bridge = WSBusBridge(bus_b, "ws://127.0.0.1:8769", ["broadcast"])
    await bridge.start()

    received = []

    async def _collect(msg):
        received.append(msg)

    bus_a.subscribe("broadcast", _collect)

    task_a = asyncio.create_task(bus_a.start())
    task_b = asyncio.create_task(bus_b.start())

    await bus_b.publish(
        LucyMessage(
            sender="test",
            receiver="broadcast",
            type=MessageType.EVENT,
            content="bridge_test",
            data={},
        )
    )

    for _ in range(20):
        if received:
            break
        await asyncio.sleep(0.1)

    await bridge.stop()
    await gateway.stop()
    await bus_a.stop()
    await bus_b.stop()
    await task_a
    await task_b

    assert received
