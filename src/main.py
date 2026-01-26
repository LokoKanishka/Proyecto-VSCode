import json
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.engine.ollama_engine import OllamaEngine

LOG_LEVEL = os.getenv("LUCY_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("LUCY_MAIN")
logger.setLevel(getattr(logging, LOG_LEVEL, logging.INFO))
try:
    from loguru import logger as loguru_logger

    loguru_logger.remove()
    loguru_logger.add(sys.stderr, level=LOG_LEVEL)
except Exception:
    pass


def _run_prompt(engine: OllamaEngine, prompt: str) -> str:
    response_tokens = []
    for token in engine.generate_response(prompt):
        response_tokens.append(token)
        print(token, end="", flush=True)
    print("")
    return "".join(response_tokens)

def _manual_vision(engine: OllamaEngine) -> None:
    try:
        result = engine.desktop_skills.capture_screen()
        payload = json.loads(result)
        image_path = payload.get("path")
        if not image_path:
            print("⚠️ No se pudo obtener la ruta de la captura.")
            return

        analysis = engine._analyze_image(image_path)
        print(f"👁️ Captura: {image_path}")
        print(f"🧠 Análisis: {analysis}")
        if engine.tts_enabled and engine.speech:
            engine.speech.say(analysis)
    except Exception as exc:
        print(f"⚠️ Error en /vision: {exc}")


def process_interaction(engine: OllamaEngine, user_input: str) -> bool:
    if not user_input or not user_input.strip():
        return True

    lowered = user_input.lower().strip()
    if lowered in {"salir", "exit", "/quit", "apágate", "apagáte"}:
        print("👋 Apagando sistemas...")
        if engine.tts_enabled and engine.speech:
            engine.speech.say("Desconectando sistemas. Hasta luego.")
        return False
    if lowered == "/vision":
        print("🟢 Capturando pantalla...")
        _manual_vision(engine)
        return True

    print(f"\n👤 Usuario: {user_input}")
    print("🧠 Lucy pensando...")
    print("🤖 Lucy: ", end="", flush=True)
    _run_prompt(engine, user_input)
    return True


def main() -> None:
    print("\n===========================================")
    print(" 🤖 LUCY AGI - SISTEMA DE ESCRITORIO LOCAL")
    print("    (RTX 5090 | Vision & Action)          ")
    print("===========================================")

    voice_mode = os.getenv("LUCY_VOICE_MODE", "0") == "1"

    try:
        model_name = os.getenv("LUCY_MAIN_MODEL") or os.getenv("LUCY_OLLAMA_MODEL")
        if model_name:
            print(f"⚙️  Cargando Cerebro ({model_name})...")
            engine = OllamaEngine(model=model_name)
        else:
            print("⚙️  Cargando Cerebro (config.yaml o default)...")
            engine = OllamaEngine()
        print("✅ Sistemas en línea.")
    except Exception as exc:
        print(f"❌ Error crítico inicializando: {exc}")
        return

    try:
        if voice_mode:
            if not engine.speech:
                print("❌ Error: Modo Voz activado pero el puente de audio falló.")
                return

            print("👂 Escuchando continuamente... (Habla claro)")
            while True:
                text_segment = engine.speech.listen_continuous()
                if not text_segment:
                    continue
                print(f"🎤 Oído: {text_segment}")
                should_continue = process_interaction(engine, text_segment)
                if not should_continue:
                    break
        else:
            print("⌨️  Escribí tus comandos (Ctrl+C para salir)")
            while True:
                user_input = input("\n👉 Tú: ")
                should_continue = process_interaction(engine, user_input)
                if not should_continue:
                    break
    except KeyboardInterrupt:
        print("\n🛑 Interrupción de usuario.")
    except Exception as exc:
        print(f"\n❌ Error fatal en main loop: {exc}")


if __name__ == "__main__":
    main()
