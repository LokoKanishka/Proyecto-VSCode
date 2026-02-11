import asyncio
import os
import sys
from loguru import logger

# Add project root to path
sys.path.append(os.getcwd())

from src.engine.ollama_engine import OllamaEngine

async def test_vision():
    logger.info("🎬 Iniciando prueba de VISION...")
    # Initialize engine with the standardized model
    engine = OllamaEngine(model="qwen2.5:32b")
    
    prompt = "mira la pantalla y dime que ves"
    logger.info(f"❓ Prompt: {prompt}")
    
    print("\n--- RESPUESTA DE LUCY (VISION) ---")
    response_text = ""
    async for token in engine.generate_response(prompt):
        print(token, end="", flush=True)
        response_text += token
    print("\n----------------------------------")
    
    if len(response_text) > 20:
        logger.info("✅ Respuesta de vision recibida con exito.")
    else:
        logger.warning("⚠️ La respuesta de vision fue muy corta o vacia.")

if __name__ == "__main__":
    # OllamaEngine is sync but uses generators, let's wrap it correctly
    async def main():
        # engine.generate_response returns a generator
        engine = OllamaEngine(model="qwen2.5:32b")
        prompt = "mira la pantalla y dime que ves"
        print("\n--- RESPUESTA DE LUCY (VISION) ---")
        for token in engine.generate_response(prompt):
            print(token, end="", flush=True)
        print("\n----------------------------------")

    import asyncio
    # Simple sync run since generate_response is a generator
    engine = OllamaEngine(model="qwen2.5:32b")
    prompt = "mira la pantalla y dime que ves"
    print("\n--- RESPUESTA DE LUCY (VISION) ---")
    for token in engine.generate_response(prompt):
        print(token, end="", flush=True)
    print("\n----------------------------------")
