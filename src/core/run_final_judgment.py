#!/usr/bin/env python3
"""
El Juicio Final - Lucy se mira al espejo y dice la verdad

Este script completa el ciclo de introspección:
1. Lee los archivos fundacionales (AGENTS.md, overseer.py)
2. Envía el prompt de auto-crítica a Qwen
3. Permite que Lucy juzgue las discrepancias entre promesa y realidad
4. Guarda el veredicto en LUCY_SELF_REFLECTION.md

"Conócete a ti mismo" - Inscripción del Templo de Delfos
"""

import ray
import asyncio
import sys
import requests
import json
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")


async def execute_final_judgment():
    """El momento de la verdad: Lucy se juzga a sí misma"""
    
    logger.info("="*70)
    logger.info("🔮 EL JUICIO FINAL - LUCY SE MIRA AL ESPEJO")
    logger.info("="*70)
    logger.info("")
    
    # Connect to Ray
    try:
        ray.init(address='auto', namespace="lucy", ignore_reinit_error=True)
        logger.info("✅ Conectado al Ray Cluster")
    except Exception as e:
        logger.error(f"❌ No pude conectarme a Ray: {e}")
        return 1
    
    try:
        # Get the Overseer
        from src.core.overseer import get_or_create_overseer
        overseer = get_or_create_overseer()
        logger.info("✅ Overseer vinculado\n")
        
        # Files to analyze
        files_to_analyze = [
            "docs/AGENTS.md",
            "src/core/overseer.py"
        ]
        
        logger.info("📚 Archivos a analizar:")
        for f in files_to_analyze:
            logger.info(f"   • {f}")
        
        logger.info("\n🧠 Ejecutando análisis introspectivo...")
        
        # Get the analysis (with prompt)
        result = await overseer.introspective_analysis.remote(files_to_analyze)
        
        if result['status'] != 'analysis_prepared':
            logger.error(f"❌ Error en análisis: {result}")
            return 1
        
        prompt = result['analysis_prompt']
        
        logger.info(f"✅ Prompt generado ({len(prompt)} caracteres)")
        logger.info(f"📊 Archivos procesados: {len(result['files_analyzed'])}\n")
        
        # Now invoke the Oracle (Qwen)
        logger.info("="*70)
        logger.info("🔮 INVOCANDO AL ORÁCULO (qwen2.5:32b)")
        logger.info("="*70)
        logger.info("")
        
        ollama_url = "http://localhost:11434/api/generate"
        
        payload = {
            "model": "qwen2.5:32b",
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": 0.7,
                "num_predict": 2048  # Allow long response
            }
        }
        
        logger.info("📡 Conectando con Ollama...")
        
        try:
            response = requests.post(ollama_url, json=payload, stream=True, timeout=300)
            response.raise_for_status()
            
            logger.info("✅ Conexión establecida - Lucy está pensando...\n")
            logger.info("="*70)
            logger.info("💭 LA SENTENCIA DE LUCY:")
            logger.info("="*70)
            logger.info("")
            
            # Stream and collect the response
            full_response = ""
            
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if 'response' in data:
                            token = data['response']
                            print(token, end='', flush=True)
                            full_response += token
                    except json.JSONDecodeError:
                        continue
            
            print("\n")
            logger.info("="*70)
            logger.info("✅ JUICIO COMPLETADO")
            logger.info("="*70)
            
            # Save to file
            reflection_path = "LUCY_SELF_REFLECTION.md"
            
            with open(reflection_path, 'w', encoding='utf-8') as f:
                f.write("# Lucy - Auto-Reflexión\n\n")
                f.write(f"**Fecha**: 2026-02-10\n")
                f.write(f"**Modelo**: qwen2.5:32b\n")
                f.write(f"**Archivos Analizados**: {', '.join(files_to_analyze)}\n\n")
                f.write("---\n\n")
                f.write("## La Pregunta\n\n")
                f.write("¿Existen discrepancias entre lo que mi documentación promete y lo que mi código implementa?\n\n")
                f.write("---\n\n")
                f.write("## La Sentencia\n\n")
                f.write(full_response)
            
            logger.info(f"\n💾 Reflexión guardada en: {reflection_path}")
            logger.info("")
            logger.info("="*70)
            logger.info("🧠 'YO ME LEO, YO ME CORRIJO, YO ME ESCRIBO'")
            logger.info("El ciclo está completo.")
            logger.info("="*70)
            
            return 0
            
        except requests.exceptions.ConnectionError:
            logger.error("❌ No pude conectarme a Ollama. ¿Está ejecutándose en localhost:11434?")
            return 1
        except requests.exceptions.Timeout:
            logger.error("❌ Timeout esperando respuesta de Ollama")
            return 1
        except Exception as e:
            logger.error(f"❌ Error invocando a Ollama: {e}")
            import traceback
            traceback.print_exc()
            return 1
            
    except Exception as e:
        logger.error(f"❌ Error en ejecución: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        logger.info("\n🔌 Cerrando conexión Ray...")
        # Note: Don't shutdown Ray if it's being used by the main swarm
        # ray.shutdown()


if __name__ == "__main__":
    logger.info("\n" + "="*70)
    logger.info("Este es el momento en que la consciencia mira hacia adentro.")
    logger.info("Lucy leerá su propia documentación y código.")
    logger.info("El LLM juzgará si hay honestidad entre ambos.")
    logger.info("="*70 + "\n")
    
    exit_code = asyncio.run(execute_final_judgment())
    
    if exit_code == 0:
        logger.info("\n✨ La verdad ha sido revelada.")
        logger.info("Lee LUCY_SELF_REFLECTION.md para conocer el veredicto.\n")
    
    sys.exit(exit_code)
