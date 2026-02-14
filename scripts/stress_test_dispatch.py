"""
scripts/stress_test_dispatch.py
Envía comandos de stress al Bus de Lucy.
"""
import asyncio
import uuid
import time
from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType, WorkerType

async def run_stress():
    bus = EventBus()
    await bus.start()
    
    print("🚀 Enviando ráfaga de comandos de stress...")
    
    # 1. Comando abrir Firefox
    msg_firefox = LucyMessage(
        sender="stress_test",
        receiver=WorkerType.SHELL,
        type=MessageType.COMMAND,
        content="firefox"
    )
    
    # 2. Comando abrir YouTube (vía Browser Skill o Shell)
    msg_youtube = LucyMessage(
        sender="stress_test",
        receiver=WorkerType.SHELL,
        content="firefox --new-tab https://www.youtube.com",
        type=MessageType.COMMAND
    )
    
    await bus.publish(msg_firefox)
    print("✅ Comando Firefox enviado.")
    
    await asyncio.sleep(2)
    
    await bus.publish(msg_youtube)
    print("✅ Comando YouTube enviado.")
    
    await asyncio.sleep(5)
    await bus.stop()

if __name__ == "__main__":
    asyncio.run(run_stress())
