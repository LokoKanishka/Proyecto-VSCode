from src.skills.base_skill import BaseSkill
from duckduckgo_search import DDGS
import json
from typing import Dict, Any
from loguru import logger

class WebSearchSkill(BaseSkill):
    def __init__(self):
        self._ddgs = DDGS()

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return "Realiza una búsqueda en internet para obtener información actualizada y veraz sobre eventos recientes, datos técnicos o cultura general."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "La consulta de búsqueda optimizada para un motor de búsqueda (ej: 'precio bitcoin hoy', 'clima en Madrid')."
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str) -> str:
        logger.info(f"Ejecutando búsqueda web: {query}")
        try:
            results = list(self._ddgs.text(query, max_results=5))
            if not results:
                return "No se encontraron resultados para esta búsqueda."
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error en WebSearchSkill: {e}")
            return f"Error en la búsqueda: {str(e)}"
