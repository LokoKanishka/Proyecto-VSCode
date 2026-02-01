import asyncio
import json
import logging
import uuid
from collections import deque
import os
import time
from typing import Iterable, Optional

import ssl
import websockets

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)
BRIDGE_METRICS_LOG = "logs/bridge_metrics.jsonl"

def _percentile(values, pct: int):
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100) * (len(ordered) - 1)))
    return round(float(ordered[idx]), 2)


class WSBusBridge:
    """
    Bridge WS para replicar tópicos del bus entre nodos.
    """

    def __init__(self, bus: EventBus, url: str, topics: Iterable[str]):
        self.bus = bus
        self.url = url
        self.topics = {topic for topic in topics if topic}
        self.bridge_id = f"bridge-{uuid.uuid4().hex[:8]}"
        self.max_hops = int(os.getenv("LUCY_WS_BRIDGE_MAX_HOPS", "2"))
        self._task: Optional[asyncio.Task] = None
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._sender_task: Optional[asyncio.Task] = None
        self._outbound_queue: asyncio.Queue = asyncio.Queue(
            maxsize=int(os.getenv("LUCY_WS_BRIDGE_QUEUE", "200"))
        )
        self._metrics = {"sent": 0, "received": 0, "dropped": 0}
        self._latency_ms = deque(maxlen=200)
        self._backlog_max = 0
        self._backlog_warn = int(os.getenv("LUCY_WS_BRIDGE_BACKLOG_WARN", "120"))
        self._last_backlog_warn = 0.0
        self._last_stats_emit = 0.0
        self._seen = set()
        self._seen_fifo = deque(maxlen=2000)
        for topic in self.topics:
            self.bus.subscribe(topic, self._forward_local)
        self.bus.subscribe("bridge_control", self._handle_control)

    async def start(self) -> None:
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
        if self._sender_task:
            self._sender_task.cancel()
            await asyncio.gather(self._sender_task, return_exceptions=True)
        if self._ws:
            await self._ws.close()

    async def _run(self) -> None:
        backoff = 1.0
        max_backoff = float(os.getenv("LUCY_WS_BRIDGE_BACKOFF_MAX", "12"))
        while True:
            try:
                async with websockets.connect(self.url, ssl=_build_client_ssl()) as ws:
                    backoff = 1.0
                    self._ws = ws
                    if self._sender_task:
                        self._sender_task.cancel()
                        await asyncio.gather(self._sender_task, return_exceptions=True)
                    self._sender_task = asyncio.create_task(self._sender_loop())
                    await ws.send(json.dumps({"action": "subscribe", "topics": list(self.topics), "token": _bridge_token()}))
                    async for raw in ws:
                        try:
                            payload = json.loads(raw)
                            message_payload = payload.get("message")
                            if not message_payload:
                                continue
                            msg = LucyMessage.model_validate(message_payload)
                            if msg.id in self._seen:
                                continue
                            if msg.data.get("origin") == self.bridge_id:
                                continue
                            if msg.data.get("bridge_hops", 0) >= self.max_hops:
                                continue
                            sent_ts = msg.data.get("bridge_ts")
                            if sent_ts:
                                try:
                                    self._latency_ms.append((time.time() - float(sent_ts)) * 1000.0)
                                except Exception:
                                    pass
                            self._track_seen(msg.id)
                            self._metrics["received"] += 1
                            await self.bus.publish(msg)
                            if self._metrics["received"] % 200 == 0:
                                latency = (
                                    sum(self._latency_ms) / len(self._latency_ms)
                                    if self._latency_ms
                                    else 0.0
                                )
                                logger.info(
                                    "WSBridge stats sent=%s recv=%s dropped=%s backlog_max=%s latency_avg_ms=%.1f",
                                    self._metrics["sent"],
                                    self._metrics["received"],
                                    self._metrics["dropped"],
                                    self._backlog_max,
                                    latency,
                                )
                            await self._emit_stats_event(latency)
                        except Exception as exc:
                            logger.debug("WSBusBridge inbound error: %s", exc)
            except Exception as exc:
                logger.warning("WSBusBridge reconnecting: %s", exc)
                jitter = 0.2 + (0.6 * (time.time() % 1))
                await asyncio.sleep(min(max_backoff, backoff) + jitter)
                backoff = min(max_backoff, backoff * 2)

    async def _forward_local(self, message: LucyMessage) -> None:
        if message.data.get("origin") == self.bridge_id:
            return
        if message.id in self._seen:
            return
        payload = message.model_dump()
        hops = int(message.data.get("bridge_hops", 0)) + 1
        if hops > self.max_hops:
            return
        payload["data"] = {
            **message.data,
            "origin": self.bridge_id,
            "bridge_hops": hops,
            "bridge_ts": time.time(),
        }
        try:
            self._track_seen(message.id)
            if self._outbound_queue.full():
                try:
                    self._outbound_queue.get_nowait()
                    self._outbound_queue.task_done()
                except Exception:
                    pass
                self._metrics["dropped"] += 1
            await self._outbound_queue.put(json.dumps({"action": "publish", "message": payload, "token": _bridge_token()}))
            if self._outbound_queue.qsize() > self._backlog_max:
                self._backlog_max = self._outbound_queue.qsize()
            if self._backlog_max >= self._backlog_warn:
                now = time.time()
                if now - self._last_backlog_warn > 10.0:
                    self._last_backlog_warn = now
                    logger.warning("WSBridge backlog alto: %s", self._backlog_max)
                    await self.bus.publish(
                        LucyMessage(
                            sender="ws_bridge",
                            receiver="broadcast",
                            type=MessageType.EVENT,
                            content="bridge_backpressure",
                            data={"backlog": self._backlog_max, "url": self.url},
                        )
                    )
            await self._maybe_emit_stats()
        except Exception as exc:
            logger.debug("WSBusBridge outbound error: %s", exc)

    def _track_seen(self, msg_id: str) -> None:
        if msg_id in self._seen:
            return
        self._seen.add(msg_id)
        self._seen_fifo.append(msg_id)
        while len(self._seen_fifo) > self._seen_fifo.maxlen:
            old = self._seen_fifo.popleft()
            self._seen.discard(old)

    async def _sender_loop(self) -> None:
        while True:
            try:
                payload = await self._outbound_queue.get()
                if self._ws:
                    await self._ws.send(payload)
                    self._metrics["sent"] += 1
                self._outbound_queue.task_done()
            except Exception as exc:
                logger.debug("WSBusBridge sender error: %s", exc)
                await asyncio.sleep(0.2)

    async def _handle_control(self, message: LucyMessage) -> None:
        if message.type != MessageType.COMMAND:
            return
        if message.content != "set_topics":
            return
        topics = message.data.get("topics") or []
        if not isinstance(topics, list):
            return
        self.topics = {t for t in topics if t}
        for topic in self.topics:
            self.bus.subscribe(topic, self._forward_local)


def _bridge_token() -> Optional[str]:
    return os.getenv("LUCY_WS_BRIDGE_TOKEN")


def _build_client_ssl() -> Optional[ssl.SSLContext]:
    if not os.getenv("LUCY_WS_TLS_CERT"):
        return None
    ctx = ssl.create_default_context()
    ca = os.getenv("LUCY_WS_TLS_CA")
    if ca:
        ctx.load_verify_locations(cafile=ca)
    if os.getenv("LUCY_WS_TLS_INSECURE", "0") in {"1", "true", "yes"}:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx

    async def _maybe_emit_stats(self) -> None:
        now = time.time()
        if now - self._last_stats_emit < 15.0:
            return
        latency = sum(self._latency_ms) / len(self._latency_ms) if self._latency_ms else 0.0
        await self._emit_stats_event(latency)
        self._last_stats_emit = now

    async def _emit_stats_event(self, latency: float) -> None:
        try:
            os.makedirs(os.path.dirname(BRIDGE_METRICS_LOG), exist_ok=True)
            with open(BRIDGE_METRICS_LOG, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({
                    "timestamp": time.time(),
                    "sent": self._metrics["sent"],
                    "received": self._metrics["received"],
                    "dropped": self._metrics["dropped"],
                    "backlog_max": self._backlog_max,
                    "latency_avg_ms": round(latency, 2),
                    "latency_p50_ms": _percentile(self._latency_ms, 50),
                    "latency_p95_ms": _percentile(self._latency_ms, 95),
                    "url": self.url,
                }) + "\n")
        except Exception:
            pass
        p50 = _percentile(self._latency_ms, 50)
        p95 = _percentile(self._latency_ms, 95)
        await self.bus.publish(
            LucyMessage(
                sender="ws_bridge",
                receiver="broadcast",
                type=MessageType.EVENT,
                content="bridge_stats",
                data={
                    "sent": self._metrics["sent"],
                    "received": self._metrics["received"],
                    "dropped": self._metrics["dropped"],
                    "backlog_max": self._backlog_max,
                    "latency_avg_ms": round(latency, 2),
                    "latency_p50_ms": p50,
                    "latency_p95_ms": p95,
                    "url": self.url,
                },
            )
        )
        await self.bus.publish(
            LucyMessage(
                sender="ws_bridge",
                receiver="broadcast",
                type=MessageType.EVENT,
                content="bridge_stats_audit",
                data={
                    "sent": self._metrics["sent"],
                    "received": self._metrics["received"],
                    "dropped": self._metrics["dropped"],
                    "backlog_max": self._backlog_max,
                    "latency_avg_ms": round(latency, 2),
                    "latency_p50_ms": p50,
                    "latency_p95_ms": p95,
                    "url": self.url,
                },
            )
        )
