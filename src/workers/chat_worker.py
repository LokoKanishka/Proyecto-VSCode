import logging
try:
    import ollama
    HAS_OLLAMA = True
except ImportError:
    HAS_OLLAMA = False

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)

class ChatWorker(BaseWorker):
    """
    Agente para conversación general y tareas de NLP puro.
    """
    def __init__(self, worker_id, bus):
        super().__init__(worker_id, bus)
        self.model = "qwen2.5:14b"

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        user_text = message.data.get("text", "")
        history = message.data.get("history", [])

        logger.info(f"💬 ChatWorker procesando: {user_text[:50]}...")

        if not HAS_OLLAMA:
            await self.send_response(message, "Error: Librería 'ollama' no instalada.")
            return

        try:
            messages = history + [{'role': 'user', 'content': user_text}]
            response = ollama.chat(
                model=self.model,
                messages=messages,
            )
            reply = response['message']['content']
            await self.send_response(message, reply)
        except Exception as e:
            logger.error(f"Error en chat: {e}")
            await self.send_error(message, str(e))
