import asyncio
from src.engine.orchestrator import LucyOrchestrator
from loguru import logger

async def main():
    logger.info("🧪 Iniciando Prueba de Integración de Lucy Monolítica...")
    
    # 1. Inicializar Orquestador
    # Usamos un modelo que soporte tools. Asegúrate de que esté instalado en Ollama.
    orchestrator = LucyOrchestrator(model="llama3") 
    
    # 2. Prueba de Enrutamiento Rápido (System Control)
    logger.info("\n--- Prueba 1: Enrutamiento Rápido ---")
    async for token in orchestrator.process_input("Sube el volumen"):
        print(token, end="", flush=True)
    print("\n")

    # 3. Prueba de Razonamiento + Herramientas (Web Search)
    logger.info("\n--- Prueba 2: Búsqueda Web (Tool Calling) ---")
    async for token in orchestrator.process_input("Busca quién ganó el último mundial de fútbol"):
        print(token, end="", flush=True)
    print("\n")

    # 4. Prueba de Memoria (RAG)
    logger.info("\n--- Prueba 3: Memoria a largo plazo ---")
    async for token in orchestrator.process_input("¿Qué te pedí que buscaras hace un momento?"):
        print(token, end="", flush=True)
    print("\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.error(f"Fallo en la prueba de integración: {e}")
