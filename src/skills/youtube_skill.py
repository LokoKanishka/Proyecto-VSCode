from src.skills.base_skill import BaseSkill
import webbrowser
import urllib.parse
from typing import Dict, Any
from loguru import logger

class YoutubeSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "youtube_search"

    @property
    def description(self) -> str:
        return "Busca videos en YouTube y los abre en el navegador predeterminado."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "El término de búsqueda para encontrar el video (ej: 'musica lofi', 'tutorial python')."
                }
            },
            "required": ["query"]
        }

    def execute(self, query: str) -> str:
        logger.info(f"Buscando en YouTube: {query}")
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.youtube.com/results?search_query={encoded_query}"
            webbrowser.open(url)
            return f"He abierto YouTube con los resultados de búsqueda para: '{query}'."
        except Exception as e:
            logger.error(f"Error en YoutubeSkill: {e}")
            return f"No pude abrir YouTube: {str(e)}"
