import asyncio

import pytest

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType


@pytest.mark.asyncio
async def test_publish_and_wait_response():
    bus = EventBus()

    async def worker_handler(message: LucyMessage):
        response = LucyMessage(
            sender="worker",
            receiver=message.sender,
            type=MessageType.RESPONSE,
            content=f"ack {message.content}",
            in_reply_to=message.id,
        )
        await bus.publish(response)

    bus.subscribe("worker_target", worker_handler)
    bus_task = asyncio.create_task(bus.start())
    try:
        request = LucyMessage(
            sender="manager",
            receiver="worker_target",
            type=MessageType.COMMAND,
            content="hola",
        )
        response = await bus.publish_and_wait(request, timeout=1.0)
        assert response.content == "ack hola"
        metrics = bus.get_metrics()
        assert metrics["responses"] == 1
    finally:
        await bus.stop()
        await bus_task


@pytest.mark.asyncio
async def test_publish_and_wait_propagates_error():
    bus = EventBus()

    async def worker_handler(message: LucyMessage):
        error_response = LucyMessage(
            sender="worker",
            receiver=message.sender,
            type=MessageType.ERROR,
            content="boom",
            in_reply_to=message.id,
        )
        await bus.publish(error_response)

    bus.subscribe("worker_target", worker_handler)
    bus_task = asyncio.create_task(bus.start())
    try:
        request = LucyMessage(
            sender="manager",
            receiver="worker_target",
            type=MessageType.COMMAND,
            content="fail",
        )
        with pytest.raises(RuntimeError):
            await bus.publish_and_wait(request, timeout=1.0)
        metrics = bus.get_metrics()
        assert metrics["errors"] == 1
    finally:
        await bus.stop()
        await bus_task
