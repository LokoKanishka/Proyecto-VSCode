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
                metadata TEXT
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
        
        conn.commit()
        conn.close()
        logger.info(f"💾 Memoria inicializada en {self.db_path}")

    def add_message(self, entry: MemoryEntry):
        """Guarda un mensaje."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        embedding = entry.embedding or self._encode_text(entry.content)
        cursor.execute('''
            INSERT INTO messages (id, timestamp, role, content, session_id, embedding, audio_path, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            entry.id, entry.timestamp, entry.role, entry.content, entry.session_id, 
            json.dumps(embedding) if embedding else None,
            entry.audio_path, "{}"
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
