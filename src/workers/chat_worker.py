import logging
from typing import List

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
        self.blocklist = {"violencia", "suicidio", "autolesion", "nazi"}

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        user_text = message.data.get("text", "")
        history = message.data.get("history", [])
        stream = bool(message.data.get("stream", False))
        override_model = message.data.get("model")
        delegate = message.data.get("delegate")

        logger.info(f"💬 ChatWorker procesando: {user_text[:50]}...")

        if not HAS_OLLAMA:
            await self.send_response(message, "Error: Librería 'ollama' no instalada.")
            return
        if self._is_blocked(user_text):
            await self.send_response(message, "No puedo ayudar con ese contenido.")
            return

        try:
            messages = history + [{'role': 'user', 'content': user_text}]
            model = override_model or self.model
            if delegate:
                await self.send_event("chat_delegate_request", {"delegate": delegate, "text": user_text})
            if stream:
                reply_chunks: List[str] = []
                for chunk in ollama.chat(model=model, messages=messages, stream=True):
                    part = chunk.get("message", {}).get("content", "")
                    if part:
                        reply_chunks.append(part)
                        await self.send_event("chat_partial", {"content": part})
                reply = "".join(reply_chunks)
            else:
                response = ollama.chat(
                    model=model,
                    messages=messages,
                )
                reply = response['message']['content']
            await self.send_response(message, reply, {"model": model})
        except Exception as e:
            logger.error(f"Error en chat: {e}")
            await self.send_error(message, str(e))

    def _is_blocked(self, text: str) -> bool:
        lower = (text or "").lower()
        return any(word in lower for word in self.blocklist)
