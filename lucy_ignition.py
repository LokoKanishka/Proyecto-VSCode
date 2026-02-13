"""
LUCY IGNITION - Protocolo de Arranque Paralelo.
Ubicación: lucy_ignition.py
"""
import ray
import time
import asyncio
import os
import sys
from loguru import logger

# Asegurar que src está en el path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from src.core.aleph_nucleus import AlephNucleus
from src.core.memory_actor import MemoryActor
from src.core.thought_actor import ThoughtActor
from src.core.vision_actor import VisionActor
from src.core.action_actor import ActionActor

async def ignite_system():
    logger.info("🔥 INICIANDO PROTOCOLO DE IGNICIÓN PARALELA (LUCY ALEPH)...")
    start_time = time.time()

    # 1. Iniciar Ray
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)
    
    # 2. Despliegue de Actores (Async Gather)
    logger.info("🚀 Desplegando actores en el clúster...")
    
    # Instanciación de actores con nombres registrados
    nucleus = AlephNucleus.options(name="AlephNucleus").remote()
    memory = MemoryActor.options(name="MemoryActor").remote()
    thought = ThoughtActor.options(name="ThoughtActor").remote()
    vision = VisionActor.options(name="VisionActor").remote()
    action = ActionActor.options(name="ActionActor").remote()
    
    # Esperar confirmación de vida (health check básico)
    tasks = [
        nucleus.get_hardware_telemetry.remote(),
        memory.get_stats.remote(),
        thought.health_check.remote(),
        vision.capture_screen.remote(),
        action.health_check.remote()
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, res in enumerate(results):
        actor_names = ["Nucleus", "Memory", "Thought", "Vision", "Action"]
        name = actor_names[i] if i < len(actor_names) else f"Actor {i}"
        
        if isinstance(res, Exception):
            logger.error(f"❌ Fallo en ignición de {name}: {res}")
        else:
            # Simplificar salida para log
            log_res = str(res)[:100] + "..." if len(str(res)) > 100 else str(res)
            logger.success(f"✅ {name} OPERATIVO: {log_res}")

    total_time = time.time() - start_time
    logger.info(f"✨ SISTEMA SOBERANO ONLINE en {total_time:.2f} segundos.")
    
    # Mantener vivo el loop principal
    while True:
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(ignite_system())
    except KeyboardInterrupt:
        logger.info("🛑 Apagando sistema...")
        ray.shutdown()
