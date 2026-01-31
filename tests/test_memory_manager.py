import sqlite3

from src.core.types import MemoryEntry
from src.memory.memory_manager import MemoryManager


import numpy as np


class DummyEncoder:
    def encode(self, text, convert_to_numpy=True):
        return np.array([0.0])


def test_memory_summary(tmp_path, monkeypatch):
    db_file = tmp_path / "memory.db"
    manager = MemoryManager(db_path=str(db_file))
    manager.encoder = DummyEncoder()

    for i in range(30):
        entry = MemoryEntry(
            role="assistant" if i % 2 == 0 else "user",
            content=f"Mensaje {i}",
            session_id="sesion"
        )
        manager.add_message(entry)

    assert manager.count_messages("sesion") == 30
    summary_id = manager.summarize_history("sesion", limit=20)
    assert summary_id is not None
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT condensed FROM messages WHERE session_id = ? AND condensed = 1", ("sesion",))
    rows = cursor.fetchall()
    conn.close()
    assert len(rows) == 20


def test_plan_logging(tmp_path):
    db_file = tmp_path / "memory.db"
    manager = MemoryManager(db_path=str(db_file))
    manager.encoder = DummyEncoder()

    manager.log_plan("plan1", "busca un video", [{"action": "search_youtube", "target": "browser_worker", "args": {"query": "video"}, "rationale": "buscar video"}])
    plan = manager.get_last_plan()
    assert plan is not None
    assert plan["id"] == "plan1"
    assert plan["prompt"] == "busca un video"
    assert plan["steps"][0]["action"] == "search_youtube"
