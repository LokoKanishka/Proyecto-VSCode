import json
import asyncio
from typing import Dict

import websockets


async def send_message(url: str, message: Dict) -> Dict:
    async with websockets.connect(url) as ws:
        await ws.send(json.dumps(message))
        raw = await ws.recv()
        return json.loads(raw)


def send_message_sync(url: str, message: Dict) -> Dict:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        raise RuntimeError("Event loop activo; use send_message async.")
    return loop.run_until_complete(send_message(url, message))
