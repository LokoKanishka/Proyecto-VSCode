import asyncio
from typing import Optional
from src.core.lucy_types import LucyMessage, MessageType, WorkerType
from src.core.bus import EventBus
from loguru import logger

class BaseWorker:
    """Clase base para todos los Workers de Lucy."""
    def __init__(self, worker_id: str, bus: EventBus):
        self.worker_id = worker_id
        self.bus = bus
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self):
        self.running = True
        logger.info(f"✅ Worker {self.worker_id} Iniciado.")
        self.bus.subscribe(self.worker_id, self.handle_message)

    async def stop(self):
        self.running = False
        logger.info(f"🛑 Worker {self.worker_id} Detenido.")

    async def handle_message(self, message: LucyMessage):
        """Método a sobreescribir por subclases."""
        pass

    async def send_response(self, original_msg: LucyMessage, content: str, data: dict = None):
        response = LucyMessage(
            sender=self.worker_id,
            receiver=original_msg.sender,
            type=MessageType.RESPONSE,
            content=content,
            data=data or {},
            in_reply_to=original_msg.id
        )
        await self.bus.publish(response)

    async def send_error(self, original_msg: LucyMessage, error_msg: str):
        error = LucyMessage(
            sender=self.worker_id,
            receiver=original_msg.sender,
            type=MessageType.ERROR,
            content=error_msg,
            in_reply_to=original_msg.id
        )
        await self.bus.publish(error)
