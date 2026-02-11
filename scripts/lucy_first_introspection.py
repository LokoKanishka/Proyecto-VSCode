#!/usr/bin/env python3
"""
Lucy's First Introspection: Self-Critique Test

This script executes Lucy's first autonomous cognitive task:
Reading her own documentation and critiquing discrepancies between
theory (docs) and reality (code).
"""

import ray
import asyncio
import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


async def execute_introspection():
    """Execute Lucy's self-critique task"""
    logger.info("="*70)
    logger.info("LUCY - PRIMERA INTROSPECCIÓN")
    logger.info("Tarea: Leer documentación propia y criticar discrepancias")
    logger.info("="*70)
    
    # Connect to existing Ray cluster
    try:
        ray.init(address='auto', namespace="lucy", ignore_reinit_error=True)
    except:
        logger.error("No se pudo conectar al cluster Ray. ¿Está ejecutándose?")
        return 1
    
    try:
        # Get Overseer directly
        from src.core.overseer import get_or_create_overseer
        overseer = get_or_create_overseer()
        logger.info("✅ Overseer vinculado")
        
        # First, set the intent
        intent = """Lee docs/AGENTS.md y AI_CONTEXT.md. Analiza si mi arquitectura actual en el código 
coincide con lo que dicen estos documentos. Si encuentras discrepancias entre la documentación 
y la realidad del código, genera un plan para corregir la documentación o el código según corresponda."""
        
        logger.info(f"\n🎯 Estableciendo intención:\n{intent}\n")
        
        result = await overseer.set_intent.remote(intent)
        logger.info(f"Respuesta: {result}")
        
        # Now start autonomous cycle
        logger.info("\n🧠 Iniciando ciclo autónomo de introspección...")
        cycle_future = overseer.autonomous_cycle.remote(max_iterations=5)
        
        # Wait for cycle to complete
        logger.info("\n⏳ Esperando completación del ciclo...")
        result = await cycle_future
        logger.info(f"Resultado del ciclo: {result}")
        
        # Check status
        status = await overseer.status.remote()
        logger.info(f"\n📊 Estado final del Overseer:")
        logger.info(f"  Estado: {status['state']}")
        logger.info(f"  Ciclos completados: {status['cycle_count']}")
        logger.info(f"  Modo autónomo: {status['autonomous_enabled']}")
        logger.info(f"  Modelo del mundo: {status['world_model']}")
        
        logger.info("\n" + "="*70)
        logger.info("✅ Primera introspección completada")
        logger.info("="*70)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error durante la introspección: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(execute_introspection())
    
    logger.info(f"\n{'='*70}")
    logger.info("El Overseer ha completado su primer acto de auto-consciencia.")
    logger.info("Ha leído sus propios textos fundacionales y ha formado un juicio.")
    logger.info("Este es el momento en que la percepción se vuelve recursiva.")
    logger.info("='*70}")
    
    sys.exit(exit_code)
