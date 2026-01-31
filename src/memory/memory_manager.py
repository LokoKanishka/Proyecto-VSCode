import sqlite3
import json
import time
import logging
import uuid
from typing import List, Dict, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from src.core.types import MemoryEntry

logger = logging.getLogger(__name__)

class MemoryManager:
    """
    Gestor de persistencia híbrido con memoria semántica (RAG).
    Combina SQLite para historial y SentenceTransformers para búsquedas vectoriales.
    """
    def __init__(
        self,
        db_path: str = "lucy_memory.db",
        vector_index_path: Optional[str] = None,
        model_name: str = "all-MiniLM-L6-v2",
    ):
        self.db_path = db_path
        self.vector_index_path = vector_index_path
        self.encoder = SentenceTransformer(model_name)
        self._init_db()

    def _init_db(self):
        """Inicializa el esquema SQLite."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                role TEXT,
                content TEXT,
                session_id TEXT,
                embedding BLOB,
                audio_path TEXT,
                metadata TEXT,
                condensed INTEGER DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                type TEXT,
                details TEXT,
                session_id TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                id TEXT PRIMARY KEY,
                path TEXT,
                content BLOB,
                hash TEXT,
                metadata TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plan_logs (
                id TEXT PRIMARY KEY,
                timestamp REAL,
                prompt TEXT,
                steps TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"💾 Memoria inicializada en {self.db_path}")
        self._ensure_schema()

    def _ensure_schema(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(messages)")
        columns = [row[1] for row in cursor.fetchall()]
        if "condensed" not in columns:
            cursor.execute("ALTER TABLE messages ADD COLUMN condensed INTEGER DEFAULT 0")
        conn.commit()
        conn.close()

    def add_message(
        self,
        entry: MemoryEntry,
        metadata: Optional[Dict] = None,
        condensed: bool = False,
    ):
        """Guarda un mensaje."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        embedding = entry.embedding or self._encode_text(entry.content)
        metadata_json = json.dumps(metadata or {})
        cursor.execute('''
            INSERT INTO messages (id, timestamp, role, content, session_id, embedding, audio_path, metadata, condensed)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.id, entry.timestamp, entry.role, entry.content, entry.session_id,
            json.dumps(embedding) if embedding else None,
            entry.audio_path, metadata_json, 1 if condensed else 0
        ))
        conn.commit()
        conn.close()

    def get_context(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Recupera contexto reciente (short-term memory)."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, content FROM messages 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (session_id, limit))
        rows = cursor.fetchall()
        conn.close()
        return [{"role": r["role"], "content": r["content"]} for r in rows][::-1]

    def log_event(self, event_type: str, details: Dict, session_id: str):
        """Auditoría de eventos del sistema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (id, timestamp, type, details, session_id)
            VALUES (?, ?, ?, ?, ?)
        ''', (str(uuid.uuid4()), time.time(), event_type, json.dumps(details), session_id))
        conn.commit()
        conn.close()

    def retrieve_relevant(self, query: str, k: int = 5) -> List[Dict[str, str]]:
        """Recupera recuerdos semánticos similares a la consulta."""
        if not query:
            return []

        query_vec = np.array(self._encode_text(query))
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT role, content, embedding FROM messages
            WHERE embedding IS NOT NULL
        ''')

        scored: List[Dict[str, str]] = []
        for role, content, embedding_json in cursor.fetchall():
            if not embedding_json:
                continue
            try:
                emb = np.array(json.loads(embedding_json))
            except (json.JSONDecodeError, TypeError):
                continue

            score = self._cosine_similarity(query_vec, emb)
            scored.append({"role": role, "content": content, "score": score})

        conn.close()
        scored.sort(key=lambda entry: entry["score"], reverse=True)
        return scored[:k]

    def log_plan(self, plan_id: str, prompt: str, plan_steps: List[Dict[str, str]]):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO plan_logs (id, timestamp, prompt, steps)
            VALUES (?, ?, ?, ?)
        ''', (
            plan_id, time.time(), prompt, json.dumps(plan_steps)
        ))
        conn.commit()
        conn.close()

    def get_last_plan(self) -> Optional[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, prompt, steps, timestamp FROM plan_logs
            ORDER BY timestamp DESC LIMIT 1
        ''')
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row["id"],
            "prompt": row["prompt"],
            "steps": json.loads(row["steps"]),
            "timestamp": row["timestamp"]
        }

    def get_events(self, session_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = '''
            SELECT type, details, timestamp FROM events
        '''
        params: List = []
        if session_id:
            query += " WHERE session_id = ?"
            params.append(session_id)
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        cursor.execute(query, tuple(params))
        rows = cursor.fetchall()
        conn.close()
        return [
            {
                "type": row["type"],
                "details": json.loads(row["details"]),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]

    def count_messages(self, session_id: str) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM messages WHERE session_id = ?
        ''', (session_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def summarize_history(self, session_id: str, limit: int = 25) -> Optional[str]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, role, content FROM messages
            WHERE session_id = ? AND condensed = 0
            ORDER BY timestamp DESC
            LIMIT ?
        ''', (session_id, limit))
        rows = cursor.fetchall()
        if len(rows) < limit:
            conn.close()
            return None
        summary_lines = [
            f"[{row['role']}] {row['content'][:120].strip()}"
            for row in rows[::-1][:5]
        ]
        summary_text = "Resumen automático: " + " | ".join(summary_lines)
        entry = MemoryEntry(
            role="system",
            content=summary_text,
            session_id=session_id,
        )
        summary_id = entry.id
        self.add_message(entry, metadata={"summary_of": [row["id"] for row in rows]})
        self._mark_condensed([row["id"] for row in rows])
        conn.close()
        return summary_id

    def _mark_condensed(self, ids: List[str]):
        if not ids:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        placeholders = ",".join("?" for _ in ids)
        cursor.execute(
            f"UPDATE messages SET condensed = 1 WHERE id IN ({placeholders})",
            ids
        )
        conn.commit()
        conn.close()

    def _encode_text(self, text: str) -> List[float]:
        if not text:
            return []
        vector = self.encoder.encode(text, convert_to_numpy=True)
        return vector.tolist()

    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        if not a.any() or not b.any():
            return 0.0
        denom = np.linalg.norm(a) * np.linalg.norm(b)
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)
