from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer, util
import torch
from loguru import logger

class SemanticRouter:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", device: str = None):
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        
        logger.info(f"Cargando SemanticRouter con el modelo {model_name} en {device}")
        self.encoder = SentenceTransformer(model_name, device=device)
        self.routes: Dict[str, torch.Tensor] = {}
        self.threshold = 0.45  # Umbral de similitud para activar una ruta

    def register_route(self, route_name: str, utterances: List[str]):
        """
        Registra una nueva ruta con ejemplos de frases (utterances).
        Pre-calcula los embeddings para evitar latencia en tiempo de ejecución.
        """
        logger.debug(f"Registrando ruta: {route_name} con {len(utterances)} frases")
        embeddings = self.encoder.encode(utterances, convert_to_tensor=True)
        self.routes[route_name] = embeddings

    def route(self, user_input: str) -> str:
        """
        Clasifica la entrada del usuario en una ruta conocida o 'default'.
        """
        if not user_input or not self.routes:
            return "default"

        # Codificar entrada
        input_emb = self.encoder.encode(user_input, convert_to_tensor=True)
        
        best_route = "default" # Ruta por defecto (Chat con LLM)
        max_score = -1.0

        for route_name, route_embs in self.routes.items():
            # Calcular similitud coseno con todos los ejemplos de la ruta
            cosine_scores = util.cos_sim(input_emb, route_embs)
            # Tomar el score máximo de coincidencia
            score = torch.max(cosine_scores).item()
            
            if score > max_score:
                max_score = score
                if max_score >= self.threshold:
                    best_route = route_name

        logger.debug(f"Intención detectada: {best_route} (score: {max_score:.4f})")
        return best_route
