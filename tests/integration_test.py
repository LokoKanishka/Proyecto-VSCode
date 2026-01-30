import asyncio
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.bus import EventBus
from src.core.types import LucyMessage, MessageType, WorkerType
from src.memory.memory_manager import MemoryManager
from src.core.manager import Manager
from src.workers.search_worker import SearchWorker
from src.workers.code_worker import CodeWorker
from src.workers.vision_worker import VisionWorker
from src.workers.chat_worker import ChatWorker

logging.basicConfig(level=logging.INFO, format='%(name)s | %(message)s')
logger = logging.getLogger("Integracion")

async def main():
    logger.info("🧩 INICIANDO TEST DE INTEGRACIÓN TOTAL")

    bus = EventBus()
    memory = MemoryManager("integration_memory.db")

    manager = Manager(bus, memory)
    searcher = SearchWorker(WorkerType.SEARCH, bus)
    coder = CodeWorker(WorkerType.CODE, bus)
    vision = VisionWorker(WorkerType.VISION, bus)
    chat = ChatWorker(WorkerType.CHAT, bus)

    bus_task = asyncio.create_task(bus.start())
    await asyncio.sleep(1)

    logger.info("\n--- 👁️ PRUEBA DE VISIÓN ---")
    await bus.publish(LucyMessage(
        sender="ui",
        receiver="user_input",
        type=MessageType.EVENT,
        content="Lucy, mira la pantalla y dime qué ves"
    ))
    await asyncio.sleep(5)

    logger.info("\n--- 💬 PRUEBA DE CHAT ---")
    await bus.publish(LucyMessage(
        sender="ui",
        receiver="user_input",
        type=MessageType.EVENT,
        content="Hola Lucy, ¿quién eres?"
    ))
    await asyncio.sleep(3)

    logger.info("\n--- 🔎 PRUEBA DE BÚSQUEDA ---")
    await bus.publish(LucyMessage(
        sender="ui",
        receiver="user_input",
        type=MessageType.EVENT,
        content="Lucy, busca cómo mejorar la conversación"
    ))
    await asyncio.sleep(3)

    logger.info("\n--- 🐍 PRUEBA DE CÓDIGO ---")
    await bus.publish(LucyMessage(
        sender="ui",
        receiver="user_input",
        type=MessageType.EVENT,
        content="Lucy, ejecuta un script para mostrar un saludo"
    ))
    await asyncio.sleep(3)

    logger.info("\n🛑 FINALIZANDO...")
    await bus.stop()
    await bus_task

    if os.path.exists("integration_memory.db"):
        os.remove("integration_memory.db")
    logger.info("✅ INTEGRACIÓN COMPLETADA")

if __name__ == "__main__":
    asyncio.run(main())
