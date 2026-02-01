from src.planners.ollama_planner import _parse_steps
from src.core.types import WorkerType


def test_parse_steps_basic():
    raw = '[{"action": "search", "target": "search", "args": {"query": "lucy"}}]'
    steps = _parse_steps(raw, max_steps=4)
    assert len(steps) == 1
    assert steps[0].action == "search"
    assert steps[0].target == WorkerType.SEARCH
    assert steps[0].args["query"] == "lucy"


def test_parse_steps_default_action_for_target():
    raw = '[{"target": "browser", "args": {"url": "https://example.com"}}]'
    steps = _parse_steps(raw, max_steps=4)
    assert len(steps) == 1
    assert steps[0].target == WorkerType.BROWSER
    assert steps[0].action == "open_url"
