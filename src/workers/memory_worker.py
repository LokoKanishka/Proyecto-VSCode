import logging
from typing import Optional

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType, WorkerType
from src.memory.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class MemoryWorker(BaseWorker):
    """Worker especializado en operaciones sobre la memoria persistente."""

    def __init__(self, worker_id: str, bus, memory: MemoryManager):
        super().__init__(worker_id, bus)
        self.memory = memory

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        if message.content == "summarize_history":
            session_id = message.data.get("session_id", "current_session")
            limit = int(message.data.get("limit", 20))
            summary_id = self.memory.summarize_history(session_id, limit=limit)
            if summary_id:
                await self.send_response(
                    message,
                    "Resumen guardado en la memoria.",
                    {"summary_id": summary_id},
                )
            else:
                await self.send_response(
                    message,
                    "No había suficiente contenido nuevo para resumir.",
                )
        elif message.content == "summarize_history_llm":
            session_id = message.data.get("session_id", "current_session")
            limit = int(message.data.get("limit", 20))
            model = message.data.get("model")
            host = message.data.get("host")
            summary_id = self.memory.summarize_history_llm(session_id, limit=limit, model=model, host=host)
            if summary_id:
                await self.send_response(
                    message,
                    "Resumen LLM guardado en la memoria.",
                    {"summary_id": summary_id},
                )
            else:
                await self.send_response(
                    message,
                    "No se pudo generar resumen LLM.",
                )
        elif message.content == "retrieve_semantic":
            query = message.data.get("query", "")
            results = self.memory.semantic_search(query, k=int(message.data.get("limit", 5)))
            await self.send_response(
                message,
                "Recuperación semántica completada.",
                {"results": results},
            )
        elif message.content == "backup_memory":
            dest = self.memory.backup_db()
            if dest:
                await self.send_response(
                    message,
                    "Backup generado.",
                    {"path": dest},
                )
            else:
                await self.send_response(
                    message,
                    "No se pudo generar backup.",
                )
        elif message.content == "build_faiss":
            ok = self.memory.build_faiss_index(limit=int(message.data.get("limit", 5000)))
            await self.send_response(
                message,
                "Índice FAISS actualizado." if ok else "No se pudo crear índice FAISS.",
                {"success": ok},
            )
        else:
            await self.send_error(message, f"Comando desconocido en MemoryWorker: {message.content}")
