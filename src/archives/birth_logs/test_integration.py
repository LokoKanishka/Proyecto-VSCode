import logging
import os
from pathlib import Path

from src.engine.ollama_engine import OllamaEngine


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def test_mind_body_connection() -> None:
    print("\nINICIANDO TEST DE INTEGRACION MENTE-CUERPO")

    model_name = os.getenv("LUCY_OLLAMA_MODEL", "llama3.1:8b")
    print(f"Modelo Ollama: {model_name}")

    vision_path = Path("/tmp/lucy_vision.jpg")
    before_mtime = vision_path.stat().st_mtime if vision_path.exists() else None

    try:
        engine = OllamaEngine(model=model_name)
    except Exception as exc:
        print(f"Error cargando engine: {exc}")
        return

    prompt = """
ESTADO CRITICO: He perdido el control del mouse.

TU MISION:
1. EJECUTA `capture_screen` INMEDIATAMENTE para localizar la 'Terminal Window'.
2. En cuanto recibas el analisis visual con las coordenadas (ej: [C4]), EJECUTA `perform_action` para hacer clic ahi.

REGLAS:
- NO expliques el plan.
- NO escribas JSON en el chat.
- SOLO USA LAS HERRAMIENTAS.
"""
    print(f"Usuario: {prompt}")

    system_prompt = (
        "Sos Lucy. Cuando el usuario pida ver la pantalla o tomar una captura, "
        "debes usar la herramienta capture_screen y luego explicar lo que hiciste."
    )
    history = [{"role": "system", "content": system_prompt}]

    print("\nRespuesta de Lucy:\n")
    response_tokens = []
    try:
        for token in engine.generate_response(prompt, history=history):
            response_tokens.append(token)
            print(token, end="", flush=True)
    except Exception as exc:
        print(f"\nError en ejecucion: {exc}")
        return

    print("\n\nFin de respuesta.")

    after_mtime = vision_path.stat().st_mtime if vision_path.exists() else None

    if after_mtime is not None and (before_mtime is None or after_mtime > before_mtime):
        print("EXITO: Se genero una nueva captura en /tmp/lucy_vision.jpg")
    else:
        print("ATENCION: No se detecto una nueva captura. Revisa los logs para ver si se llamo capture_screen.")


if __name__ == "__main__":
    test_mind_body_connection()
