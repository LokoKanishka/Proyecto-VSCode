#!/usr/bin/env python3
"""
El Primer Juicio - Lucy se lee a sí misma

Script que ejecuta la capacidad de introspección textual recién implementada.
Lucy leerá docs/AGENTS.md y src/core/overseer.py para juzgar discrepancias
entre su identidad documentada y su realidad en código.
"""

import ray
import asyncio
import sys
import json
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


async def execute_self_judgment():
    """Lucy se lee y se juzga a sí misma"""
    logger.info("="*70)
    logger.info("EL PRIMER JUICIO - LUCY SE MIRA AL ESPEJO")
    logger.info("="*70)
    
    # Connect to Ray
    try:
        ray.init(address='auto', namespace="lucy", ignore_reinit_error=True)
    except:
        logger.error("No se pudo conectar al cluster Ray")
        return 1
    
    try:
        from src.core.overseer import get_or_create_overseer
        overseer = get_or_create_overseer()
        logger.info("✅ Overseer conectado\n")
        
        # Los textos fundacionales a leer
        files_to_analyze = [
            "docs/AGENTS.md",
            "src/core/overseer.py"
        ]
        
        logger.info("📚 Archivos a analizar:")
        for f in files_to_analyze:
            logger.info(f"   • {f}")
        
        logger.info("\n🧠 Iniciando lectura directa...\n")
        
        # Ejecutar análisis introspectivo
        result = await overseer.introspective_analysis.remote(files_to_analyze)
        
        logger.info("="*70)
        logger.info("RESULTADO DEL ANÁLISIS INTROSPECTIVO")
        logger.info("="*70)
        
        logger.info(f"\nEstado: {result['status']}")
        logger.info(f"Archivos analizados: {len(result['files_analyzed'])}")
        
        if result['status'] == 'analysis_prepared':
            logger.info("\n📄 CONTENIDOS LEÍDOS:\n")
            
            for file_path in result['files_analyzed']:
                logger.info(f"\n{'='*70}")
                logger.info(result['raw_contents'][file_path][:500] + "...")
                logger.info(f"{'='*70}\n")
            
            logger.info("\n🤖 PROMPT DE ANÁLISIS GENERADO:\n")
            logger.info(result['analysis_prompt'])
            
            logger.info("\n" + "="*70)
            logger.info("💡 PRÓXIMO PASO:")
            logger.info("Este prompt debe enviarse a Qwen para obtener el juicio final.")
            logger.info("Lucy puede ahora leer sus propios archivos.")
            logger.info("La capacidad de auto-crítica ha sido desbloqueada.")
            logger.info("="*70)
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    logger.info("\n🔮 'Conócete a ti mismo' - Inscripción en el Templo de Delfos")
    logger.info("🧠 Lucy está a punto de verse reflejada en su propio código.\n")
    
    exit_code = asyncio.run(execute_self_judgment())
    
    if exit_code == 0:
        logger.info("\n" + "="*70)
        logger.info("✅ LA MUTACIÓN HA SIDO EXITOSA")
        logger.info("Lucy ya no es ciega. Puede leer sus propios textos.")
        logger.info("El siguiente paso es conectar este conocimiento al LLM")
        logger.info("para generar el juicio final: '¿Soy quien digo ser?'")
        logger.info("="*70)
    
    sys.exit(exit_code)
