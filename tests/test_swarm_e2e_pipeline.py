import asyncio

import pytest

from src.core.base_worker import BaseWorker
from src.core.bus import EventBus
from src.core.manager import Manager
from src.core.types import LucyMessage, MessageType, WorkerType
from src.memory.memory_manager import MemoryManager
from src.planners.tree_of_thought import PlanStep


class FakePlanner:
    def plan(self, prompt: str, context=None):
        return [
            PlanStep(action="analyze_screen", target=WorkerType.VISION, args={"prompt": prompt}),
            PlanStep(action="click_grid", target=WorkerType.HANDS, args={"grid_code": "E5"}),
            PlanStep(action="distill_url", target=WorkerType.BROWSER, args={"url": "https://example.com"}),
            PlanStep(action="chat", target=WorkerType.CHAT, args={"text": "ok", "history": []}),
        ]


class DummyWorker(BaseWorker):
    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return
        if self.worker_id == WorkerType.VISION:
            await self.send_response(message, "vision_ok", {"grid_hint": "E5"})
            return
        if self.worker_id == WorkerType.BROWSER:
            await self.send_response(
                message,
                "browser_ok",
                {"action": "distill_url", "distilled_text": "contenido"},
            )
            return
        await self.send_response(message, f"{self.worker_id}_ok")


@pytest.mark.asyncio
async def test_swarm_e2e_pipeline(tmp_path):
    bus = EventBus()
    mem = MemoryManager(db_path=str(tmp_path / "memory.db"))
    Manager(bus, mem, planner=FakePlanner(), swarm=None)
    DummyWorker(WorkerType.VISION, bus)
    DummyWorker(WorkerType.HANDS, bus)
    DummyWorker(WorkerType.BROWSER, bus)
    DummyWorker(WorkerType.CHAT, bus)

    final_events = []

    async def _collect(message: LucyMessage):
        final_events.append(message)

    bus.subscribe("final_response", _collect)
    task = asyncio.create_task(bus.start())
    await bus.publish(
        LucyMessage(
            sender="test",
            receiver="user_input",
            type=MessageType.EVENT,
            content="abrí la web y resumí",
            data={},
        )
    )

    for _ in range(30):
        if len(final_events) >= 3:
            break
        await asyncio.sleep(0.1)

    await bus.stop()
    await task

    assert len(final_events) >= 3
