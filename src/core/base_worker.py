import asyncio
from abc import ABC, abstractmethod
from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

class BaseWorker(ABC):
    """
    Clase base para workers del enjambre.
    Maneja la conexión al bus y el ciclo de vida.
    """
    def __init__(self, worker_id: str, bus: EventBus):
        self.worker_id = worker_id
        self.bus = bus
        self.bus.subscribe(self.worker_id, self.handle_message)

    @abstractmethod
    async def handle_message(self, message: LucyMessage):
        """Lógica específica del worker."""
        pass

    async def send_response(self, original_msg: LucyMessage, content: str, data: dict = None):
        """Responder al remitente (Manager)."""
        response = LucyMessage(
            sender=self.worker_id,
            receiver=original_msg.sender,
            type=MessageType.RESPONSE,
            content=content,
            data=data or {},
            in_reply_to=original_msg.id,
        )
        await self.bus.publish(response)

    async def send_error(self, original_msg: LucyMessage, error_msg: str):
        """Reportar error."""
        response = LucyMessage(
            sender=self.worker_id,
            receiver=original_msg.sender,
            type=MessageType.ERROR,
            content=error_msg,
            in_reply_to=original_msg.id,
        )
        await self.bus.publish(response)

    async def send_event(self, receiver: str, content: str, data: dict | None = None):
        """Publicar eventos secundarios (ej. salida final)."""
        event = LucyMessage(
            sender=self.worker_id,
            receiver=receiver,
            type=MessageType.EVENT,
            content=content,
            data=data or {}
        )
        await self.bus.publish(event)
