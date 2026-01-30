import logging
from typing import List

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class CodeWorker(BaseWorker):
    """Ejecuta comandos de código simples."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        payload_code = message.data.get("code") if isinstance(message.data, dict) else None
        prompt = (payload_code or message.content).strip()
        logger.info("🐍 CodeWorker procesando petición de código: %s", prompt[:80])

        reply_body = self._execute_prompt(prompt)
        reply_data = {
            "script": prompt,
        }
        await self.send_response(message, reply_body, reply_data)

    def _execute_prompt(self, prompt: str) -> str:
        normalized = prompt.lower()
        if "fibonacci" in normalized:
            sequence = self._fibonacci(10)
            return f"Fibonacci(10) = {sequence[-1]} | Serie: {sequence}"
        return f"Ejecuté de forma simulada el snippet:\n{prompt}"

    def _fibonacci(self, n: int) -> List[int]:
        seq = [0, 1]
        while len(seq) < n:
            seq.append(seq[-1] + seq[-2])
        return seq[:n]
