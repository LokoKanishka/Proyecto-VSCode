"""
LUCY ALEPH MEMORY - Actor de Memoria Distribuida (LanceDB + Synaptic Cache).
Ubicación: src/core/memory_actor.py
"""
import ray
import lancedb
import time
import os
import json
from loguru import logger
from typing import List, Dict, Any, Optional
from datetime import datetime

MEMORY_PATH = "data/aleph_memory.lance"

@ray.remote(namespace="lucy")
class MemoryActor:
    def __init__(self):
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        self.db = lancedb.connect(MEMORY_PATH)
        self._ensure_tables()
        self.synaptic_cache = {}  # Cache RAM LRU simple
        logger.info("🧠 LUCY MEMORY ACTOR: INITIALIZED")

    def _ensure_tables(self):
        # Tabla principal de conocimiento
        if "knowledge" not in self.db.table_names():
            self.db.create_table("knowledge", data=[{
                "vector": [0.0] * 768, # Dimensiones nomic-embed-text
                "content": "LUCY CORE KNOWLEDGE BASE",
                "source": "genesis",
                "timestamp": datetime.now().isoformat()
            }])

    async def store_memory(self, content: str, vector: List[float], source: str = "interaction"):
        """Almacena un nuevo recuerdo vectorial."""
        try:
            table = self.db.open_table("knowledge")
            table.add([{
                "vector": vector,
                "content": content,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }])
            # Actualizar synaptic cache (muy simple por ahora)
            self.synaptic_cache[current_time_ms()] = content
            return True
        except Exception as e:
            logger.error(f"Memory storage failed: {e}")
            return False

    async def retrieve_memory(self, query_vector: List[float], limit: int = 5) -> List[Dict[str, Any]]:
        """Recupera recuerdos semánticos cercanos."""
        try:
            table = self.db.open_table("knowledge")
            results = table.search(query_vector).limit(limit).to_list()
            return results
        except Exception as e:
            logger.error(f"Memory retrieval failed: {e}")
            return []

    async def get_stats(self):
        return {
            "tables": self.db.table_names(),
            "cache_size": len(self.synaptic_cache)
        }

def current_time_ms():
    return int(time.time() * 1000)
