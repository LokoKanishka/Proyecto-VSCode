import sqlite3
from typing import List

from src.core.types import MemoryEntry
from src.memory.memory_manager import MemoryManager


import numpy as np


class DummyEncoder:
    def encode(self, text, convert_to_numpy=True):
        return np.array([0.0])


class StubVectorStore:
    def __init__(self):
        self.saved: List[str] = []

    def save_memory(self, text: str, meta_type: str = "conversation") -> None:
        self.saved.append(f"{meta_type}:{text}")

    def recall(self, query: str, limit: int = 5) -> List[str]:
        results = [entry for entry in self.saved if query.lower() in entry.lower()]
        return results[:limit]


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


def test_semantic_search_prefers_vector_store(tmp_path):
    db_file = tmp_path / "memory.db"
    store = StubVectorStore()
    manager = MemoryManager(db_path=str(db_file), vector_store=store)
    manager.encoder = DummyEncoder()

    entry = MemoryEntry(role="assistant", content="Prueba de vector search", session_id="sesion2")
    manager.add_message(entry)

    results = manager.semantic_search("vector", k=3)
    assert isinstance(results, list)
    assert results and "vector" in results[0]["content"]
    assert store.saved, "El vector_store no recibió los mensajes guardados"


def test_semantic_search_fallback_when_vector_empty(tmp_path, monkeypatch):
    db_file = tmp_path / "memory.db"
    store = StubVectorStore()
    manager = MemoryManager(db_path=str(db_file), vector_store=store)
    manager.encoder = DummyEncoder()

    entry = MemoryEntry(role="assistant", content="Solo texto base", session_id="sesion3")
    manager.add_message(entry)

    called = False

    def fake_retrieve(query, k=5):
        nonlocal called
        called = True
        return [{"role": "assistant", "content": "fallback data"}]

    monkeypatch.setattr(manager, "retrieve_relevant", fake_retrieve)

    results = manager.semantic_search("nada", k=2)
    assert called, "No se cayó al retrieve_relevant pese a vector store vacío"
    assert results and results[0]["content"] == "fallback data"
