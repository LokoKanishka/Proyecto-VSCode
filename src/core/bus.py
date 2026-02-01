import asyncio
import json
import logging
import os
from collections import Counter
from collections import defaultdict, deque
import time
from typing import Awaitable, Callable, Dict, List, Optional

from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class EventBus:
    """
    Bus de mensajería asíncrono centralizado.
    Desacopla al Manager de los Workers.
    """
    def __init__(self, max_queue_size: int = 0):
        self._subscribers: Dict[str, List[Callable[[LucyMessage], Awaitable[None]]]] = {}
        self._queue: asyncio.Queue = asyncio.Queue(maxsize=max_queue_size or 0)
        self._running = False
        self._response_futures: Dict[str, asyncio.Future] = {}
        self._metrics: Counter = Counter()
        self._inflight: Dict[str, tuple[float, str]] = {}
        self._latency: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self._durable_path = os.getenv("LUCY_BUS_DURABLE_PATH")
        self._durable_keep = int(os.getenv("LUCY_BUS_DURABLE_KEEP", "5"))

    def get_metrics(self) -> Dict[str, int]:
        """Devuelve un snapshot de métricas del bus (publicaciones, despachos, respuestas)."""
        return {
            "published": self._metrics["published"],
            "dispatched": self._metrics["dispatched"],
            "responses": self._metrics["responses"],
            "errors": self._metrics["errors"],
            "queue_size": self._queue.qsize(),
            "queue_max": self._queue.maxsize,
        }

    def get_latency_metrics(self) -> Dict[str, float]:
        summary = {}
        for worker, values in self._latency.items():
            if not values:
                continue
            summary[worker] = round(sum(values) / len(values), 2)
        return summary

    async def start(self):
        """Inicia el loop de procesamiento."""
        self._running = True
        await self._load_durable_queue()
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
        self._metrics["published"] += 1
        if message.type == MessageType.COMMAND:
            self._inflight[message.id] = (time.time(), str(message.receiver))
        self._append_durable(message)
        await self._queue.put(message)

    async def publish_and_wait(self, message: LucyMessage, timeout: float | None = None) -> LucyMessage:
        """
        Publica un comando y espera su primer response/error correlacionado.
        """
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        self._response_futures[message.id] = future
        try:
            await self.publish(message)
            return await asyncio.wait_for(future, timeout) if timeout else await future
        finally:
            self._response_futures.pop(message.id, None)

    async def _dispatch(self, message: LucyMessage):
        """Enrutamiento de mensajes."""
        self._metrics["dispatched"] += 1
        if message.receiver in self._subscribers:
            for handler in self._subscribers[message.receiver]:
                asyncio.create_task(handler(message))
        if message.type == MessageType.EVENT and "broadcast" in self._subscribers:
            for handler in self._subscribers["broadcast"]:
                asyncio.create_task(handler(message))

        if message.type in (MessageType.RESPONSE, MessageType.ERROR) and message.in_reply_to:
            self._resolve_response(message)

    def _resolve_response(self, message: LucyMessage):
        future = self._response_futures.get(message.in_reply_to)
        if not future or future.done():
            return
        self._metrics["responses"] += 1
        start = self._inflight.pop(message.in_reply_to, None)
        if start:
            elapsed = (time.time() - start[0]) * 1000.0
            self._latency[start[1]].append(elapsed)
        if message.type == MessageType.ERROR:
            self._metrics["errors"] += 1
            future.set_exception(RuntimeError(message.content))
        else:
            future.set_result(message)

    async def _load_durable_queue(self) -> None:
        if not self._durable_path or not os.path.exists(self._durable_path):
            return
        try:
            with open(self._durable_path, "r", encoding="utf-8") as fh:
                lines = [line.strip() for line in fh if line.strip()]
            if not lines:
                return
            ts = time.strftime("%Y%m%d_%H%M%S")
            drained = f"{self._durable_path}.drain.{ts}"
            os.replace(self._durable_path, drained)
            self._rotate_durable()
            for line in lines:
                try:
                    payload = json.loads(line)
                    msg = LucyMessage.model_validate(payload)
                    msg.metadata["durable_replay"] = True
                    await self._queue.put(msg)
                except Exception as exc:
                    logger.warning("No pude rehidratar mensaje durable: %s", exc)
        except Exception as exc:
            logger.warning("No pude cargar durable queue: %s", exc)

    def _append_durable(self, message: LucyMessage) -> None:
        if not self._durable_path:
            return
        if message.type not in {MessageType.COMMAND, MessageType.EVENT}:
            return
        try:
            os.makedirs(os.path.dirname(self._durable_path) or ".", exist_ok=True)
            with open(self._durable_path, "a", encoding="utf-8") as fh:
                fh.write(message.model_dump_json() + "\n")
        except Exception as exc:
            logger.warning("No pude persistir durable queue: %s", exc)

    def _rotate_durable(self) -> None:
        if self._durable_keep <= 0 or not self._durable_path:
            return
        base = os.path.basename(self._durable_path)
        folder = os.path.dirname(self._durable_path) or "."
        try:
            files = sorted(
                [f for f in os.listdir(folder) if f.startswith(f"{base}.drain.")],
                reverse=True,
            )
            for name in files[self._durable_keep:]:
                try:
                    os.remove(os.path.join(folder, name))
                except Exception:
                    pass
        except Exception:
            pass
