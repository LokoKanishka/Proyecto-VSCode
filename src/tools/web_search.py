import logging
import time

from duckduckgo_search import DDGS
from newspaper import Article

logger = logging.getLogger(__name__)


class WebSearchTool:
    def __init__(self):
        self.ddgs = DDGS()

    def search(self, query, max_results=3):
        """Busca en DuckDuckGo y devuelve titulos y enlaces."""
        logger.info("Buscando en la web: '%s'", query)
        try:
            results = list(self.ddgs.text(query, max_results=max_results))
            return results
        except Exception as exc:
            logger.error("Error en busqueda: %s", exc)
            return []

    def read_page(self, url):
        """Descarga y extrae el texto principal de una URL."""
        logger.info("Leyendo pagina: %s", url)
        try:
            article = Article(url)
            article.download()
            article.parse()
            return article.text[:1500] + "..."
        except Exception as exc:
            logger.error("Error leyendo pagina: %s", exc)
            return "No pude leer el contenido de esta pagina."


if __name__ == "__main__":
    tool = WebSearchTool()
    time.sleep(0.1)
    print(tool.search("Teoria del Basilisco de Roko"))
