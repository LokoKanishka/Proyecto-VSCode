from src.workers.code_worker import CodeWorker
from src.core.bus import EventBus


def test_code_worker_snippet_match(monkeypatch):
    bus = EventBus()
    worker = CodeWorker("code_worker", bus)
    monkeypatch.setattr(worker, "snippets", [
        {"name": "csv", "keywords": ["csv"], "code": "print('csv')"}
    ])
    reply, data = worker._execute_prompt("necesito leer csv")
    assert "print('csv')" in reply
    assert data["mode"] == "snippet"
