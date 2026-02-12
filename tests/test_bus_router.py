import asyncio

from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType
from src.core.base_worker import BaseWorker


class DummyWorker(BaseWorker):
    async def handle_message(self, message: LucyMessage):
        if message.type == MessageType.COMMAND:
            await self.send_response(message, "ok", {"echo": message.content})


async def _run_bus_test():
    bus = EventBus()
    DummyWorker("dummy", bus)
    bus_task = asyncio.create_task(bus.start())
    try:
        msg = LucyMessage(
            sender="tester",
            receiver="dummy",
            type=MessageType.COMMAND,
            content="ping",
            data={},
        )
        response = await bus.publish_and_wait(msg, timeout=2)
        assert response.content == "ok"
        assert response.data["echo"] == "ping"
    finally:
        await bus.stop()
        await bus_task


def test_bus_publish_and_wait():
    asyncio.run(_run_bus_test())
