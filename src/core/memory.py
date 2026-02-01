import ray
import lancedb
from sentence_transformers import SentenceTransformer
import os
from loguru import logger
import pandas as pd
from typing import List, Dict, Any

@ray.remote
class MemoryActor:
    """
    Long-term Memory for Lucy using LanceDB.
    Handles semantic search and persistent storage of interactions/knowledge.
    """
    def __init__(self):
        logger.info("🧠 MemoryActor initializing...")
        
        # Paths
        self.db_path = os.path.expanduser("~/.lucy/memory/lancedb")
        os.makedirs(self.db_path, exist_ok=True)
        
        # Initialize DB
        self.db = lancedb.connect(self.db_path)
        self.table_name = "knowledge_base"
        
        # Initialize Embedding Model (CPU-friendly default)
        # Note: In production we might want to put this on GPU or use a lighter model
        logger.info("🧠 Loading embedding model (all-MiniLM-L6-v2)...")
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Ensure table exists
        self._init_table()
        logger.info("✅ MemoryActor ready.")

    def _init_table(self):
        if self.table_name not in self.db.table_names():
            # Create schema by inserting a dummy record then deleting it, or defining pyarrow schema
            # LanceDB supports creating from list of dicts.
            # Schema: vector (384 dim), text (str), source (str), timestamp (float)
            data = [{"vector": self.encoder.encode("init").tolist(), "text": "init", "source": "system", "timestamp": 0.0}]
            self.db.create_table(self.table_name, data=data)
            logger.info(f"📚 Created new table: {self.table_name}")
        else:
            logger.info(f"📚 Connected to existing table: {self.table_name}")

    async def add(self, text: str, source: str = "user"):
        """
        Add a text chunk to memory.
        """
        logger.info(f"💾 Memorizing: {text[:50]}...")
        vector = self.encoder.encode(text).tolist()
        data = [{"vector": vector, "text": text, "source": source, "timestamp": 0.0}] # TODO: real timestamp
        
        tbl = self.db.open_table(self.table_name)
        tbl.add(data)
        logger.debug("✅ Saved to LanceDB.")
        return True

    async def search(self, query: str, k: int = 3) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context.
        """
        logger.info(f"🔍 Searching memory for: {query}")
        vector = self.encoder.encode(query).tolist()
        
        tbl = self.db.open_table(self.table_name)
        results = tbl.search(vector).limit(k).to_pandas()
        
        # Convert to list of dicts
        out = results.to_dict(orient="records")
        for item in out:
            # Clean up vector data from output if not needed
            if "vector" in item:
                del item["vector"]
        return out
