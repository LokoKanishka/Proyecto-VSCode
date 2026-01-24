import asyncio
from src.engine.orchestrator import LucyOrchestrator
from loguru import logger
import sys

# Función envoltorio para imitar el "Paso 3" del usuario pero usando el motor avanzado
async def test_maestro():
    print("--- 🧪 INICIANDO TEST MAESTRO (Monolito Avanzado V4) ---")
    
    # 1. Inicializar el Orquestador con soporte para Tools y Memoria
    # Usamos llama3 como solicitó el usuario
    try:
        orchestrator = LucyOrchestrator(model="llama3.1")
    except Exception as e:
        print(f"❌ Error iniciando Lucy: {e}")
        return

    # Caso 1: Pregunta que requiere Internet (USARÁ WEB_SEARCH SKILL)
    prompt = "Busca en la web qué precio tiene el dolar blue en Argentina hoy"
    print(f"\n👤 Usuario: {prompt}")

    print("\n🧠 Lucy está pensando y decidiendo qué herramienta usar...")
    
    full_response = ""
    async for token in orchestrator.process_input(prompt):
        print(token, end="", flush=True)
        full_response += token
    
    print("\n\n✅ TEST COMPLETADO")
    print("-" * 50)
    print("Nota: Este test utilizó el Orquestador V4 con Routing Semántico y Memoria LanceDB.")

if __name__ == "__main__":
    try:
        asyncio.run(test_maestro())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Error en el test: {e}")
