import sqlite3
import json
import time
import logging
import uuid
import os
import shutil
import subprocess
import requests
import hashlib
import base64
import zlib
from typing import Any, Dict, List, Optional, Protocol

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss  # type: ignore
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

from src.core.lucy_types import MemoryEntry

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
        model_name: str = "nomic-embed-text",  # CHANGED: Technical embeddings specialized
        vector_store: Optional[VectorStoreProtocol] = None,
        use_ollama: bool = True,  # NEW: Prefer Ollama embeddings
    ):
        self.db_path = db_path
        self.vector_index_path = vector_index_path
        
        # Initialize encoder - UPGRADED to technical embeddings
        if os.getenv("LUCY_NO_EMB", "0") in {"1", "true", "yes"}:
            self.encoder = _DummyEncoder()
            logger.info("🔇 Embeddings disabled (LUCY_NO_EMB=1)")
        elif use_ollama:
            # Use Ollama embeddings (nomic-embed-text for technical code understanding)
            try:
                from src.memory.ollama_embeddings import OllamaEmbeddings
                self.encoder = OllamaEmbeddings(model=model_name)
                logger.info(f"🧠 Technical embeddings active: {model_name} via Ollama")
            except Exception as e:
                logger.warning(f"⚠️ Ollama embeddings failed ({e}), falling back to SentenceTransformer")
                self.encoder = SentenceTransformer("all-MiniLM-L6-v2")
        else:
            # Fallback to SentenceTransformers (generic embeddings)
            self.encoder = SentenceTransformer(model_name)
            logger.info(f"📚 Generic embeddings: {model_name}")
        
        self.vector_store = vector_store
        self.faiss_index = None
        self.faiss_dim = None
        self.faiss_texts: List[str] = []
        self._init_db()
        if HAS_FAISS and self.vector_index_path and os.path.exists(self.vector_index_path):
            try:
                self.faiss_index = faiss.read_index(self.vector_index_path)
                self.faiss_dim = self.faiss_index.d
            except Exception:
                self.faiss_index = None

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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS embeddings_cache (
                key TEXT PRIMARY KEY,
                hash TEXT,
                embedding BLOB,
                updated_at REAL
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
        if os.getenv("LUCY_FAISS_ALWAYS_ON", "0") in {"1", "true", "yes"}:
            self._append_faiss(entry)

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
        self._prune_events(conn)
        conn.close()

    def _prune_events(self, conn: sqlite3.Connection) -> None:
        """Aplica retención y límites de tamaño sobre la tabla events."""
        retention_days = float(os.getenv("LUCY_EVENTS_RETENTION_DAYS", "30"))
        max_rows = int(os.getenv("LUCY_EVENTS_MAX_ROWS", "20000"))
        cursor = conn.cursor()
        if retention_days > 0:
            cutoff = time.time() - (retention_days * 86400)
            cursor.execute("DELETE FROM events WHERE timestamp < ?", (cutoff,))
        if max_rows > 0:
            cursor.execute(
                "DELETE FROM events WHERE id IN ("
                "SELECT id FROM events ORDER BY timestamp DESC LIMIT -1 OFFSET ?"
                ")",
                (max_rows,),
            )
        conn.commit()

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

    def log_file_snapshot(self, path: str, content: bytes, metadata: Optional[Dict] = None) -> Optional[str]:
        if not path:
            return None
        file_id = str(uuid.uuid4())
        sha = hashlib.sha256(content).hexdigest() if content is not None else None
        compress_threshold = int(os.getenv("LUCY_SNAPSHOT_COMPRESS_THRESHOLD", "200000"))
        compressor = os.getenv("LUCY_SNAPSHOT_COMPRESSOR", "zlib").lower()
        compressed = False
        blob = content
        if content is not None and len(content) >= compress_threshold:
            try:
                if compressor == "lz4":
                    try:
                        import lz4.frame  # type: ignore
                        blob = lz4.frame.compress(content)
                        compressed = True
                    except Exception:
                        blob = zlib.compress(content, level=6)
                        compressed = True
                else:
                    blob = zlib.compress(content, level=6)
                    compressed = True
            except Exception:
                blob = content
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO files (id, path, content, hash, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            file_id,
            path,
            blob,
            sha,
            json.dumps({
                **(metadata or {}),
                "compressed": compressed,
                "compressor": compressor if compressed else None,
                "timestamp": time.time(),
            }),
        ))
        conn.commit()
        self._prune_file_snapshots(conn)
        conn.close()
        return file_id

    def _prune_file_snapshots(self, conn: sqlite3.Connection) -> None:
        max_count = int(os.getenv("LUCY_SNAPSHOT_MAX_COUNT", "5000"))
        max_bytes = int(os.getenv("LUCY_SNAPSHOT_MAX_BYTES", "1073741824"))
        max_age_days = float(os.getenv("LUCY_SNAPSHOT_MAX_AGE_DAYS", "0"))
        cursor = conn.cursor()
        if max_age_days > 0:
            cutoff = time.time() - (max_age_days * 86400)
            try:
                cursor.execute(
                    "DELETE FROM files WHERE id IN ("
                    "SELECT id FROM files WHERE json_extract(metadata, '$.timestamp') < ?"
                    ")",
                    (cutoff,),
                )
            except Exception:
                pass
        if max_count > 0:
            cursor.execute(
                "DELETE FROM files WHERE id IN ("
                "SELECT id FROM files ORDER BY rowid DESC LIMIT -1 OFFSET ?"
                ")",
                (max_count,),
            )
        if max_bytes > 0:
            cursor.execute("SELECT COALESCE(SUM(LENGTH(content)), 0) FROM files")
            total = cursor.fetchone()[0] or 0
            while total > max_bytes:
                cursor.execute(
                    "SELECT id, COALESCE(LENGTH(content),0) FROM files ORDER BY rowid ASC LIMIT 1"
                )
                row = cursor.fetchone()
                if not row:
                    break
                cursor.execute("DELETE FROM files WHERE id = ?", (row[0],))
                total -= int(row[1] or 0)
        conn.commit()

    def export_snapshots_jsonl(self, path: str) -> int:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT id, path, content, hash, metadata FROM files")
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return 0
        with open(path, "w", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps({
                    "id": row[0],
                    "path": row[1],
                    "content_b64": base64.b64encode(row[2] or b"").decode("utf-8"),
                    "hash": row[3],
                    "metadata": json.loads(row[4]) if row[4] else {},
                }) + "\n")
        return len(rows)

    def import_snapshots_jsonl(self, path: str) -> int:
        if not os.path.exists(path):
            return 0
        count = 0
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                if not line.strip():
                    continue
                data = json.loads(line)
                content = base64.b64decode(data.get("content_b64", "") or "")
                self.log_file_snapshot(
                    data.get("path", ""),
                    content,
                    metadata=data.get("metadata") or {},
                )
                count += 1
        return count

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

    def summarize_hierarchical(
        self,
        session_id: str,
        chunk_size: int = 25,
        model: Optional[str] = None,
        host: Optional[str] = None,
    ) -> Optional[str]:
        rows = self._fetch_uncondensed(session_id)
        if len(rows) < chunk_size:
            return None
        summaries: List[str] = []
        summary_ids: List[str] = []
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            chunk_text = "\n".join(f"[{row['role']}] {row['content']}" for row in chunk)
            summary = self._call_ollama(
                "Resumí en 3-4 frases concisas:\n\n" + chunk_text,
                model=model,
                host=host,
            ) or self._heuristic_summary(chunk)
            entry = MemoryEntry(
                role="system",
                content="Resumen automático: " + summary.strip(),
                session_id=session_id,
            )
            self.add_message(entry, metadata={"summary_level": 1, "summary_of": [row["id"] for row in chunk]})
            summary_ids.append(entry.id)
            summaries.append(summary)
            self._mark_condensed([row["id"] for row in chunk])
        if len(summaries) < 2:
            return summary_ids[-1] if summary_ids else None
        merged = "\n".join(f"- {text}" for text in summaries)
        final_summary = self._call_ollama(
            "Resumí los siguientes resúmenes en 4-6 frases:\n\n" + merged,
            model=model,
            host=host,
        ) or " | ".join(summaries[:5])
        final_entry = MemoryEntry(
            role="system",
            content="Resumen jerárquico: " + final_summary.strip(),
            session_id=session_id,
        )
        self.add_message(final_entry, metadata={"summary_level": 2, "summary_of": summary_ids})
        return final_entry.id

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

    def _fetch_uncondensed(self, session_id: str) -> List[sqlite3.Row]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, role, content FROM messages
            WHERE session_id = ? AND condensed = 0
            ORDER BY timestamp ASC
        ''', (session_id,))
        rows = cursor.fetchall()
        conn.close()
        return rows

    @staticmethod
    def _heuristic_summary(rows: List[sqlite3.Row]) -> str:
        sample = rows[:5]
        summary_lines = [
            f"[{row['role']}] {row['content'][:120].strip()}"
            for row in sample
        ]
        return " | ".join(summary_lines)

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
        cached = self._get_cached_embedding(text)
        if cached is not None:
            return cached
        vector = self.encoder.encode(text, convert_to_numpy=True)
        embedding = vector.tolist()
        self._set_cached_embedding(text, embedding)
        return embedding

    def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        if os.getenv("LUCY_EMB_CACHE", "1").lower() not in {"1", "true", "yes"}:
            return None
        key = self._embedding_key(text)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT hash, embedding FROM embeddings_cache WHERE key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        if row[0] != self._embedding_hash(text):
            return None
        try:
            return json.loads(row[1]) if row[1] else None
        except Exception:
            return None

    def _set_cached_embedding(self, text: str, embedding: List[float]) -> None:
        if os.getenv("LUCY_EMB_CACHE", "1").lower() not in {"1", "true", "yes"}:
            return
        key = self._embedding_key(text)
        sha = self._embedding_hash(text)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO embeddings_cache (key, hash, embedding, updated_at) VALUES (?, ?, ?, ?)",
            (key, sha, json.dumps(embedding), time.time()),
        )
        conn.commit()
        self._prune_embedding_cache(conn)
        conn.close()

    def _prune_embedding_cache(self, conn: sqlite3.Connection) -> None:
        max_rows = int(os.getenv("LUCY_EMB_CACHE_MAX", "10000"))
        if max_rows <= 0:
            return
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM embeddings_cache WHERE key IN ("
            "SELECT key FROM embeddings_cache ORDER BY updated_at DESC LIMIT -1 OFFSET ?"
            ")",
            (max_rows,),
        )
        conn.commit()

    @staticmethod
    def _embedding_hash(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _embedding_key(text: str) -> str:
        return f"text:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"

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
        require_encryption = os.getenv("LUCY_BACKUP_REQUIRE_ENCRYPTION", "0") in {"1", "true", "yes"}
        passphrase = os.getenv("LUCY_BACKUP_PASSPHRASE")
        if require_encryption and not passphrase:
            logger.warning("Backup requiere cifrado pero no hay passphrase.")
            return None
        os.makedirs(backup_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(backup_dir, f"lucy_memory_{timestamp}.db")
        keep = int(os.getenv("LUCY_BACKUP_KEEP", "5"))
        try:
            shutil.copy2(self.db_path, dest)
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
                except Exception as exc:
                    logger.warning("No pude cifrar backup: %s", exc)
                    if require_encryption:
                        return None
            self._rotate_backups(backup_dir, keep=keep)
            return dest
        except OSError as exc:
            logger.warning("No pude crear backup: %s", exc)
            return None

    def _rotate_backups(self, backup_dir: str, keep: int = 5) -> None:
        if keep <= 0:
            return
        try:
            files = sorted(
                [f for f in os.listdir(backup_dir) if f.startswith("lucy_memory_")],
                reverse=True,
            )
            for name in files[keep:]:
                try:
                    os.remove(os.path.join(backup_dir, name))
                except Exception:
                    pass
        except Exception:
            pass

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

    def _append_faiss(self, entry: MemoryEntry) -> None:
        if not HAS_FAISS or not entry.content:
            return
        if entry.embedding:
            vec = np.array(entry.embedding, dtype="float32")
        else:
            vec = np.array(self._encode_text(entry.content), dtype="float32")
        if vec.size == 0:
            return
        if self.faiss_index is None:
            self.faiss_dim = int(vec.shape[0])
            self.faiss_index = faiss.IndexFlatIP(self.faiss_dim)
        if vec.shape[0] != self.faiss_dim:
            return
        vec = vec.reshape(1, -1)
        faiss.normalize_L2(vec)
        self.faiss_index.add(vec)
        self.faiss_texts.append(entry.content)
