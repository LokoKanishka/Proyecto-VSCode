import asyncio
import logging
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType
from src.memory.memory_manager import MemoryManager
from src.core.manager import Manager
from src.workers.chat_worker import ChatWorker

logging.basicConfig(level=logging.INFO, format='%(name)s | %(message)s')
logger = logging.getLogger("TestMemoria")

async def main():
    logger.info("🧠 INICIANDO TEST DE MEMORIA SEMÁNTICA")

    bus = EventBus()
    memory = MemoryManager("memory_test.db", "memory_test.index")

    manager = Manager(bus, memory)
    chat = ChatWorker("chat_worker", bus)

    bus_task = asyncio.create_task(bus.start())
    await asyncio.sleep(1)

    logger.info("\n--- FASE 1: ENSEÑANDO DATO CLAVE ---")
    secret = "La clave secreta del proyecto es 'Elefante Rosa'."
    await bus.publish(LucyMessage(
        sender="ui", receiver="user_input", type=MessageType.EVENT,
        content=f"Lucy, guarda esto: {secret}"
    ))

    await asyncio.sleep(5)

    logger.info("\n--- FASE 2: PREGUNTANDO DATO ---")
    question = "¿Cuál es la clave secreta del proyecto?"
    await bus.publish(LucyMessage(
        sender="ui", receiver="user_input", type=MessageType.EVENT,
        content=question
    ))

    await asyncio.sleep(5)

    await bus.stop()
    await bus_task

    for f in ["memory_test.db", "memory_test.index", "memory_test.index.map"]:
        if os.path.exists(f):
            os.remove(f)

    logger.info("✅ TEST MEMORIA FINALIZADO")

if __name__ == "__main__":
    asyncio.run(main())
