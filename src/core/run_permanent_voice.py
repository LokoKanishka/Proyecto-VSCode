import asyncio
from loguru import logger
import sys
import signal

from src.engine.orchestrator import LucyOrchestrator
from src.engine.voice_bridge import LucyVoiceBridge

class PermanentVoiceMode:
    def __init__(self, model="llama3.1"):
        logger.info("🎙️ Iniciando Modo Voz Permanente (Lucy V4 Monolith)")
        self.orchestrator = LucyOrchestrator(model=model)
        self.bridge = LucyVoiceBridge()
        self.running = True

    def stop(self, signum, frame):
        logger.info("🛑 Deteniendo Lucy...")
        self.running = False

    async def run(self):
        # Capturar señales de salida
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        logger.info("✅ Lucy está en línea. Puedes empezar a hablar.")

        while self.running:
            try:
                # 1. Escuchar (Síncrono, bloqueante hasta detectar fin de frase)
                text = self.bridge.listen_continuous()
                
                if not text:
                    continue

                print(f"\n👤 Usuario: {text}")

                # 2. Procesar Cognitivamente (Asíncrono)
                full_response = ""
                print("🤖 Lucy: ", end="", flush=True)
                
                async for token in self.orchestrator.process_input(text):
                    print(token, end="", flush=True)
                    full_response += token
                
                print("\n")

                # 3. Hablar (Síncrono)
                if full_response:
                    self.bridge.say(full_response)

            except Exception as e:
                logger.error(f"⚠️ Error en el bucle de voz: {e}")
                await asyncio.sleep(1) # Pequeña pausa antes de reintentar

if __name__ == "__main__":
    # Asegurarse de que el modelo esté en Ollama
    # (El orquestador lo manejará internamente)
    
    app = PermanentVoiceMode(model="llama3.1")
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        pass
