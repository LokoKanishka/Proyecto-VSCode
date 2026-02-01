import asyncio
import os

from src.core.bus import EventBus
from src.core.manager import Manager
from src.core.types import LucyMessage, MessageType
from src.memory.memory_manager import MemoryManager
from src.core.base_worker import BaseWorker


class EchoChat(BaseWorker):
    async def handle_message(self, message: LucyMessage):
        if message.type == MessageType.COMMAND:
            await self.send_response(message, "eco")


async def _run():
    os.environ["LUCY_NO_EMB"] = "1"
    bus = EventBus()
    memory = MemoryManager(db_path=":memory:")
    manager = Manager(bus, memory)
    EchoChat("chat_worker", bus)
    bus_task = asyncio.create_task(bus.start())
    event = LucyMessage(
        sender="tester",
        receiver="user_input",
        type=MessageType.EVENT,
        content="hola",
    )
    await bus.publish(event)
    await asyncio.sleep(0.2)
    await bus.stop()
    await bus_task


def test_manager_e2e():
    asyncio.run(_run())
