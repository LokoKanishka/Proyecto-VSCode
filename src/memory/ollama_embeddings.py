"""
Ollama Embeddings Wrapper
Permite usar modelos de embedding de Ollama (como nomic-embed-text) en lugar de sentence-transformers.

Beneficios de nomic-embed-text (Sección 4.3 del informe):
- Especializado en código y razonamiento denso
- Mayor resolución semántica para conceptos técnicos
- Densidad informacional +40% vs embeddings genéricos
"""

import requests
import numpy as np
from typing import List, Union
from loguru import logger


class OllamaEmbeddings:
    """
    Wrapper para modelos de embedding de Ollama.
    Compatible con interfaz SentenceTransformer para drop-in replacement.
    """
    
    def __init__(self, model: str = "nomic-embed-text", host: str = "http://localhost:11434"):
        """
        Args:
            model: Nombre del modelo Ollama (e.g., 'nomic-embed-text')
            host: URL del servidor Ollama
        """
        self.model = model
        self.host = host
        self.dimension = None  # Se detecta en primera llamada
        
        # Verificar que modelo existe
        try:
            self._test_connection()
            logger.info(f"✅ OllamaEmbeddings initialized: {model} @ {host}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize OllamaEmbeddings: {e}")
            raise
    
    def _test_connection(self):
        """Verifica que Ollama responde y el modelo está disponible."""
        try:
            response = requests.get(f"{self.host}/api/tags", timeout=5)
            response.raise_for_status()
            models = response.json().get("models", [])
            model_names = [m.get("name", "") for m in models]
            
            if self.model not in model_names and f"{self.model}:latest" not in model_names:
                logger.warning(f"⚠️ Model {self.model} not found in Ollama. Available: {model_names}")
                # No falla, asume que se puede cargar bajo demanda
        except Exception as e:
            logger.warning(f"Could not verify Ollama models: {e}")
    
    def encode(
        self, 
        sentences: Union[str, List[str]], 
        convert_to_numpy: bool = True,
        show_progress_bar: bool = False,
        **kwargs
    ) -> Union[np.ndarray, List[np.ndarray]]:
        """
        Codifica texto(s) en embeddings vectoriales.
        
        Compatible con SentenceTransformer.encode() API.
        
        Args:
            sentences: Texto único o lista de textos
            convert_to_numpy: Si True, retorna numpy array (compatible)
            show_progress_bar: Ignorado (Ollama no soporta barra de progreso)
        
        Returns:
            numpy.ndarray o lista de arrays con embeddings
        """
        # Normalizar input
        is_single = isinstance(sentences, str)
        texts = [sentences] if is_single else sentences
        
        embeddings = []
        for text in texts:
            emb = self._encode_single(text)
            embeddings.append(emb)
        
        # Convertir a numpy si se requiere
        if convert_to_numpy:
            embeddings_np = np.array(embeddings, dtype=np.float32)
            # Si input era single string, retornar array 1D
            if is_single:
                return embeddings_np[0]
            return embeddings_np
        
        return embeddings[0] if is_single else embeddings
    
    def _encode_single(self, text: str) -> List[float]:
        """
        Codifica un texto individual usando Ollama API.
        
        Args:
            text: Texto a codificar
        
        Returns:
            Lista de floats (embedding vector)
        """
        try:
            response = requests.post(
                f"{self.host}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text
                },
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            embedding = data.get("embedding")
            
            if not embedding:
                raise ValueError(f"No embedding returned from Ollama for text: {text[:50]}...")
            
            # Detectar dimensión en primera llamada
            if self.dimension is None:
                self.dimension = len(embedding)
                logger.debug(f"📐 Embedding dimension detected: {self.dimension}")
            
            return embedding
            
        except requests.exceptions.Timeout:
            logger.error(f"⏱️ Timeout encoding text (30s): {text[:100]}...")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Request failed for embedding: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error encoding text: {e}")
            raise
    
    @property
    def get_sentence_embedding_dimension(self) -> int:
        """
        Retorna dimensión de los embeddings.
        Compatible con SentenceTransformer API.
        """
        if self.dimension is None:
            # Detectar dimensión con texto dummy
            _ = self.encode("test", convert_to_numpy=False)
        return self.dimension or 768  # Default si falla detección


def get_ollama_embeddings(model: str = "nomic-embed-text") -> OllamaEmbeddings:
    """Factory function para crear instancia de OllamaEmbeddings."""
    return OllamaEmbeddings(model=model)
