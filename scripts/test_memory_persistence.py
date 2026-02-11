#!/usr/bin/env python3
"""
Test de Continuidad - Verifica que Lucy recuerde entre sesiones

Este script prueba el Hippocampus:
1. Primera ejecución: Lucy "nace" con memoria nueva
2. Guarda pensamientos y lecciones
3. Segunda ejecución: Lucy "despierta" y recuerda
"""

import ray
import asyncio
import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


async def test_memory_persistence():
    """Test de persistencia de memoria"""
    
    logger.info("="*70)
    logger.info("TEST DE CONTINUIDAD - HIPPOCAMPUS")
    logger.info("="*70)
    
    try:
        ray.init(address='auto', namespace="lucy", ignore_reinit_error=True)
        logger.info("✅ Conectado a Ray\n")
    except:
        logger.error("Ray no está ejecutándose")
        return 1
    
    try:
        from src.core.overseer import get_or_create_overseer
        
        logger.info("📍 Creando Overseer (observa el mensaje de despertar)...\n")
        overseer = get_or_create_overseer()
        
        # Get status to see memory state
        status = await overseer.status.remote()
        
        logger.info("\n📊 ESTADO ACTUAL:")
        logger.info(f"  Estado: {status['state']}")
        logger.info(f"  Ciclos: {status['cycle_count']}")
        logger.info(f"  World Model Keys: {list(status['world_model'].keys())}")
        
        # Set an intent and save a thought
        logger.info("\n💭 Guardando un pensamiento...")
        await overseer.set_intent.remote("Probar persistencia de memoria")
        
        # Register a lesson
        logger.info("📝 Registrando una lección aprendida...")
        overseer.register_error.remote("Test: El Hippocampus funciona correctamente")
        
        await asyncio.sleep(1)  # Let it commit
        
        logger.info("\n" + "="*70)
        logger.info("✅ FASE 1 COMPLETADA")
        logger.info("Memoria guardada en lucy_consciousness.json")
        logger.info("")
        logger.info("🔄 Para probar persistencia:")
        logger.info("   1. Reinicia el Ray Swarm (Ctrl+C y vuelve a lanzar)")
        logger.info("   2. Ejecuta este script de nuevo")
        logger.info("   3. Lucy debería recordar este momento")
        logger.info("="*70)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(test_memory_persistence())
    sys.exit(exit_code)
