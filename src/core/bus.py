import asyncio
import logging
from typing import Callable, Dict, List, Awaitable
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)

class EventBus:
    """
    Bus de mensajería asíncrono centralizado.
    Desacopla al Manager de los Workers.
    """
    def __init__(self):
        self._subscribers: Dict[str, List[Callable[[LucyMessage], Awaitable[None]]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    async def start(self):
        """Inicia el loop de procesamiento."""
        self._running = True
        logger.info("🚀 EventBus iniciado.")
        while True:
            msg = await self._queue.get()
            self._queue.task_done()
            if msg is None:
                break
            await self._dispatch(msg)

    async def stop(self):
        self._running = False
        await self._queue.put(None)
        await self._queue.join()
        logger.info("🛑 EventBus detenido.")

    def subscribe(self, topic: str, handler: Callable[[LucyMessage], Awaitable[None]]):
        """Suscripción a tópicos (worker_id o 'broadcast')."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    async def publish(self, message: LucyMessage):
        """Publicar mensaje en el bus."""
        await self._queue.put(message)

    async def _dispatch(self, message: LucyMessage):
        """Enrutamiento de mensajes."""
        if message.receiver in self._subscribers:
            for handler in self._subscribers[message.receiver]:
                asyncio.create_task(handler(message))
        if message.type == MessageType.EVENT and "broadcast" in self._subscribers:
             for handler in self._subscribers["broadcast"]:
                asyncio.create_task(handler(message))
