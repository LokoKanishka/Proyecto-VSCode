import logging
import asyncio

from duckduckgo_search import DDGS

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class SearchWorker(BaseWorker):
    """Agente de Búsqueda Web Real configurable via DuckDuckGo."""

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        command = message.content
        query = message.data.get("query", "")

        logger.info("🔎 Buscando en la web: '%s'", query)

        if command == "search":
            await self.perform_real_search(message, query)
        else:
            await self.send_error(message, f"Comando desconocido: {command}")

    async def perform_real_search(self, original_msg: LucyMessage, query: str):
        try:
            loop = asyncio.get_running_loop()

            def _search():
                with DDGS() as ddgs:
                    return list(ddgs.text(query, max_results=5))

            results = await loop.run_in_executor(None, _search)

            if not results:
                await self.send_response(original_msg, f"No encontré resultados para '{query}'.")
                return

            formatted_response = f"Encontré {len(results)} resultados:\n"
            for i, res in enumerate(results, 1):
                formatted_response += f"{i}. {res['title']}: {res.get('body', '')[:100]}...\n"

            await self.send_response(
                original_msg,
                formatted_response,
                {"results": results, "source": "duckduckgo"},
            )

            await self.send_event("search_completed", {"query": query, "count": len(results)})

        except ImportError:
            await self.send_error(original_msg, "Error: 'duckduckgo_search' no está instalado.")
        except Exception as e:
            logger.error("Error crítico en búsqueda: %s", e)
            await self.send_error(original_msg, f"Falló la búsqueda: {str(e)}")
