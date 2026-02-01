from src.core.manager import Manager
from src.core.bus import EventBus
from src.memory.memory_manager import MemoryManager
from src.planners.tree_of_thought import PlanStep
from src.core.types import WorkerType


def test_manager_injects_distill_when_url_present(tmp_path):
    bus = EventBus()
    memory = MemoryManager(db_path=str(tmp_path / "lucy.db"))
    manager = Manager(bus, memory)

    plan = [
        PlanStep(
            action="chat",
            target=WorkerType.CHAT,
            args={"text": "hola"},
            rationale="fallback",
        )
    ]
    updated = manager._maybe_add_distill_step(
        "resumí esto https://example.com/nota importante",
        plan,
    )
    assert updated[0].action == "distill_url"
    assert updated[0].target == WorkerType.BROWSER
    assert updated[0].args["url"].startswith("https://example.com")
