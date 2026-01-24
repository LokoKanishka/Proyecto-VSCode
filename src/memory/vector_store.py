import lancedb
from sentence_transformers import SentenceTransformer
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import os
from loguru import logger

class EmbeddedMemory:
    def __init__(self, db_path="data/lucy_memory.lance", model_name="all-MiniLM-L6-v2"):
        """
        Inicializa la memoria persistente embebida usando LanceDB.
        """
        if not os.path.exists(os.path.dirname(db_path)):
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
        logger.info(f"Conectando a la memoria en {db_path}")
        self.db = lancedb.connect(db_path)
        
        # Usamos el mismo modelo que el Router para eficiencia (compartir VRAM si es posible)
        self.encoder = SentenceTransformer(model_name)
        
        # Configurar la tabla de interacciones
        self._setup_table()

    def _setup_table(self):
        """Prepara la tabla de interacciones si no existe."""
        table_name = "interactions"
        if table_name not in self.db.table_names():
            logger.info(f"Creando nueva tabla de memoria: {table_name}")
            # Definir esquema inicial con un dato dummy
            self.db.create_table(
                table_name,
                data=[{
                    "vector": [0.0] * 384, 
                    "text": "init", 
                    "timestamp": datetime.now().isoformat(), 
                    "type": "system"
                }],
                mode="overwrite"
            )
        
        self.table = self.db.open_table(table_name)

    def save_memory(self, text: str, meta_type: str = "conversation"):
        """Vectoriza y guarda un recuerdo en la base de datos."""
        logger.debug(f"Guardando en memoria ({meta_type}): {text[:50]}...")
        vector = self.encoder.encode(text).tolist()
        self.table.add([{
            "vector": vector,
            "text": text,
            "timestamp": datetime.now().isoformat(),
            "type": meta_type
        }])

    def recall(self, query: str, limit: int = 5) -> str:
        """Recupera contexto relevante semánticamente para una consulta."""
        logger.debug(f"Consultando memoria para: {query}")
        query_vec = self.encoder.encode(query).tolist()
        
        # Realizar búsqueda vectorial
        results = self.table.search(query_vec).limit(limit).to_pandas()
        
        if results.empty or (len(results) == 1 and results.iloc[0]['text'] == 'init'):
            return ""
            
        # Formatear contexto para inyección en el prompt del LLM
        context_parts = []
        for _, row in results.iterrows():
            if row['text'] != 'init':
                context_parts.append(f"- {row['text']}")
        
        context_str = "\n".join(context_parts)
        return context_str

    def get_recent_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """Opcional: Recuperar los últimos mensajes para memoria de corto plazo."""
        # LanceDB no es ideal para orden cronológico puro sin índices, 
        # pero podemos usar el timestamp si lo cargamos en pandas.
        results = self.table.to_pandas()
        results = results[results['text'] != 'init'].sort_values('timestamp', ascending=False)
        
        history = []
        for _, row in results.head(limit).iterrows():
            # Aquí asumimos un formato simple, se podría mejorar
            history.append({"role": "system", "content": row['text']})
            
        return history[::-1] # Invertir para orden cronológico
