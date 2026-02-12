import asyncio
import logging
import sys
import os

# Ajustar path para que encuentre los módulos src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.bus import EventBus
from src.core.lucy_types import LucyMessage, MessageType, WorkerType
from src.memory.memory_manager import MemoryManager
from src.core.manager import Manager
from src.workers.search_worker import SearchWorker
from src.workers.code_worker import CodeWorker

# Configurar logging para ver la matrix
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("SmokeTest")

async def main():
    logger.info("🧪 INICIANDO SMOKE TEST DEL ENJAMBRE")

    # 1. Inicializar Infraestructura
    bus = EventBus()
    memory = MemoryManager("test_memory.db") # Usar DB temporal

    # 2. Despertar a los Agentes
    manager = Manager(bus, memory)
    searcher = SearchWorker(WorkerType.SEARCH, bus)
    coder = CodeWorker(WorkerType.CODE, bus)

    # 3. Arrancar el Sistema Nervioso (en background)
    bus_task = asyncio.create_task(bus.start())
    
    await asyncio.sleep(1) # Calentamiento

    # --- PRUEBA 1: BÚSQUEDA WEB ---
    logger.info("\n--- 🟢 PRUEBA 1: INTENCIÓN DE BÚSQUEDA ---")
    msg_search = LucyMessage(
        sender="user_interface",
        receiver="user_input", # El Manager escucha este tópico
        type=MessageType.EVENT,
        content="Lucy, busca información sobre AGI soberana"
    )
    await bus.publish(msg_search)
    
    await asyncio.sleep(3) # Esperar procesamiento

    # --- PRUEBA 2: CÓDIGO PYTHON ---
    logger.info("\n--- 🟢 PRUEBA 2: INTENCIÓN DE CÓDIGO ---")
    msg_code = LucyMessage(
        sender="user_interface",
        receiver="user_input",
        type=MessageType.EVENT,
        content="Por favor ejecuta este script de python para calcular fibonacci"
    )
    await bus.publish(msg_code)

    await asyncio.sleep(3) # Esperar procesamiento

    # 4. Apagar todo
    logger.info("\n🛑 DETENIENDO SISTEMA...")
    await bus.stop()
    await bus_task
    
    # Limpieza (opcional)
    if os.path.exists("test_memory.db"):
        os.remove("test_memory.db")
    
    logger.info("✅ TEST COMPLETADO")

if __name__ == "__main__":
    asyncio.run(main())
