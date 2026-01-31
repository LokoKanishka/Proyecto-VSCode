import asyncio
import pytest
from pathlib import Path

from src.core.bus import EventBus
from src.watchers.file_watcher import FileWatcher
from src.watchers.notification_watcher import NotificationWatcher
from src.watchers.timer_watcher import TimerWatcher


def _collect_events(bus: EventBus):
    events = []

    async def handler(msg):
        events.append(msg)

    bus.subscribe("broadcast", handler)
    return events


@pytest.mark.asyncio
async def test_file_watcher_emits_creation_event(tmp_path):
    bus = EventBus()
    events = _collect_events(bus)
    bus_task = asyncio.create_task(bus.start())
    watcher = FileWatcher(bus, directories=[str(tmp_path)], poll_interval=0.05)
    watcher_task = asyncio.create_task(watcher.run())

    await asyncio.sleep(0.1)
    file_path = tmp_path / "nueva.txt"
    file_path.write_text("hola Lucy")
    await asyncio.sleep(0.2)

    watcher.stop()
    watcher_task.cancel()
    await asyncio.gather(watcher_task, return_exceptions=True)
    await bus.stop()
    await bus_task

    assert any(msg.content == "file_event" for msg in events)


@pytest.mark.asyncio
async def test_timer_watcher_produces_tick():
    bus = EventBus()
    events = _collect_events(bus)
    bus_task = asyncio.create_task(bus.start())
    watcher = TimerWatcher(bus, interval=0.05)
    watcher_task = asyncio.create_task(watcher.run())

    await asyncio.sleep(0.16)

    watcher.stop()
    watcher_task.cancel()
    await asyncio.gather(watcher_task, return_exceptions=True)
    await bus.stop()
    await bus_task

    assert any(msg.content == "timer_tick" for msg in events)


@pytest.mark.asyncio
async def test_notification_watcher_emits_event():
    bus = EventBus()
    events = _collect_events(bus)
    bus_task = asyncio.create_task(bus.start())
    watcher = NotificationWatcher(bus)
    await watcher._emit_event({"note": "prueba"})

    await bus.stop()
    await bus_task

    assert any(msg.content == "notification_received" for msg in events)
