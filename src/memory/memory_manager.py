import sqlite3
import json
import time
import logging
import uuid
import os
import shutil
import subprocess
import requests
from typing import Dict, List, Optional, Protocol

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss  # type: ignore
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

from src.core.types import MemoryEntry

logger = logging.getLogger(__name__)


class VectorStoreProtocol(Protocol):
    """Interfaz mínima para integrar tiendas vectoriales adicionales."""

    def save_memory(self, text: str, meta_type: str = "conversation") -> None:
        ...

    def recall(self, query: str, limit: int = 5) -> List[str]:
        ...


class _DummyEncoder:
    def encode(self, text: str, convert_to_numpy: bool = True):
        vec = np.zeros(384, dtype="float32")
        return vec


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
        vector_store: Optional[VectorStoreProtocol] = None,
    ):
        self.db_path = db_path
        self.vector_index_path = vector_index_path
        if os.getenv("LUCY_NO_EMB", "0") in {"1", "true", "yes"}:
            self.encoder = _DummyEncoder()
        else:
            self.encoder = SentenceTransformer(model_name)
        self.vector_store = vector_store
        self.faiss_index = None
        self.faiss_dim = None
        self.faiss_texts: List[str] = []
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS thought_nodes (
                id TEXT PRIMARY KEY,
                plan_id TEXT,
                parent_id TEXT,
                depth INTEGER,
                score REAL,
                content TEXT,
                metadata TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"💾 Memoria inicializada en {self.db_path}")
        self._ensure_schema()
        if os.getenv("LUCY_FAISS_ALWAYS_ON", "0") in {"1", "true", "yes"}:
            self.build_faiss_index(limit=5000)

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
        if self.vector_store and entry.content:
            meta_type = (metadata or {}).get("type", "message")
            try:
                self.vector_store.save_memory(entry.content, meta_type=meta_type)
            except Exception as exc:
                logger.warning("No se pudo guardar en vector_store: %s", exc)

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

    def semantic_search(self, query: str, k: int = 5) -> List[Dict[str, str]]:
        """Recupera contexto utilizando la tienda vectorial (si está disponible)."""
        if not query:
            return []

        if self.faiss_index is not None:
            return self._search_faiss(query, k)

        if self.vector_store:
            try:
                results = self.vector_store.recall(query, limit=k)
            except Exception as exc:
                logger.warning("Error en vector_store.recall: %s", exc)
                results = []
            if results:
                return [{"role": "assistant", "content": text} for text in results if text]
            logger.debug("Vector store regresó vacío, cayendo a retrieve_relevant")

        return self.retrieve_relevant(query, k)

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

    def summarize_history_llm(
        self,
        session_id: str,
        limit: int = 25,
        model: Optional[str] = None,
        host: Optional[str] = None,
    ) -> Optional[str]:
        rows = self._fetch_recent(session_id, limit)
        if len(rows) < limit:
            return None
        text = "\n".join(f"[{row['role']}] {row['content']}" for row in rows[::-1])
        prompt = (
            "Resumí el siguiente historial en 4-6 frases concisas, "
            "manteniendo detalles importantes:\n\n" + text
        )
        summary_text = self._call_ollama(prompt, model=model, host=host)
        if not summary_text:
            return None
        entry = MemoryEntry(
            role="system",
            content="Resumen automático: " + summary_text.strip(),
            session_id=session_id,
        )
        summary_id = entry.id
        self.add_message(entry, metadata={"summary_of": [row["id"] for row in rows]})
        self._mark_condensed([row["id"] for row in rows])
        return summary_id

    def _fetch_recent(self, session_id: str, limit: int) -> List[sqlite3.Row]:
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
        conn.close()
        return rows

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

    def backup_db(self, backup_dir: str = "backups") -> Optional[str]:
        """Copia la base de datos a un snapshot local."""
        if not os.path.exists(self.db_path):
            return None
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_dir, f"lucy_memory_{timestamp}.db")
        try:
            shutil.copy2(self.db_path, dest)
            passphrase = os.getenv("LUCY_BACKUP_PASSPHRASE")
            if passphrase:
                encrypted = f"{dest}.gpg"
                try:
                    subprocess.run(
                        ["gpg", "--batch", "--yes", "--passphrase", passphrase, "-c", dest],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if os.path.exists(encrypted):
                        return encrypted
                except Exception:
        return dest

    def log_thought_tree(self, plan_id: str, nodes: List[Dict[str, Any]]) -> None:
        if not nodes:
            return
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        for node in nodes:
            cursor.execute(
                '''
                INSERT INTO thought_nodes (id, plan_id, parent_id, depth, score, content, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    node.get("id"),
                    plan_id,
                    node.get("parent_id"),
                    node.get("depth", 0),
                    node.get("score", 0.0),
                    node.get("content", ""),
                    json.dumps(node.get("metadata", {})),
                ),
            )
        conn.commit()
        conn.close()

    def _call_ollama(
        self,
        prompt: str,
        model: Optional[str] = None,
        host: Optional[str] = None,
    ) -> Optional[str]:
        config_model = os.getenv("LUCY_OLLAMA_MODEL") or os.getenv("LUCY_MAIN_MODEL")
        config_host = os.getenv("LUCY_OLLAMA_HOST")
        model = model or config_model or "qwen2.5:14b"
        host = host or config_host or "http://localhost:11434"
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }
        try:
            response = requests.post(f"{host}/api/chat", json=payload, timeout=20)
            response.raise_for_status()
            data = response.json()
            return data.get("message", {}).get("content", "")
        except Exception as exc:
            logger.warning("LLM summary falló: %s", exc)
            return None
            return dest
        except OSError as exc:
            logger.warning("No pude crear backup: %s", exc)
            return None

    def build_faiss_index(self, limit: int = 5000) -> bool:
        """Construye un índice FAISS con los últimos embeddings (si FAISS está disponible)."""
        if not HAS_FAISS:
            logger.info("FAISS no disponible, omito índice.")
            return False
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content, embedding FROM messages WHERE embedding IS NOT NULL ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        vectors = []
        texts: List[str] = []
        for content, embedding_json in cursor.fetchall():
            if not embedding_json:
                continue
            try:
                vec = np.array(json.loads(embedding_json), dtype="float32")
            except (json.JSONDecodeError, TypeError):
                continue
            vectors.append(vec)
            texts.append(content)
        conn.close()
        if not vectors:
            return False
        mat = np.stack(vectors, axis=0)
        self.faiss_dim = mat.shape[1]
        self.faiss_index = faiss.IndexFlatIP(self.faiss_dim)
        faiss.normalize_L2(mat)
        self.faiss_index.add(mat)
        self.faiss_texts = texts
        if self.vector_index_path:
            faiss.write_index(self.faiss_index, self.vector_index_path)
        return True

    def _search_faiss(self, query: str, k: int = 5) -> List[Dict[str, str]]:
        if self.faiss_index is None:
            return []
        query_vec = np.array(self._encode_text(query), dtype="float32")
        if query_vec.size == 0:
            return []
        query_vec = query_vec.reshape(1, -1)
        faiss.normalize_L2(query_vec)
        scores, indices = self.faiss_index.search(query_vec, k)
        results: List[Dict[str, str]] = []
        for idx in indices[0]:
            if idx < 0:
                continue
            if idx < len(self.faiss_texts):
                results.append({"role": "assistant", "content": self.faiss_texts[idx]})
        return results
