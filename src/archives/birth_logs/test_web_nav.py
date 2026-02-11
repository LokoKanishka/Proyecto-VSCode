import logging
import os
import time

from src.engine.ollama_engine import OllamaEngine


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")


def run_prompt(engine: OllamaEngine, prompt: str) -> str:
    response_tokens = []
    for token in engine.generate_response(prompt):
        response_tokens.append(token)
        print(token, end="", flush=True)
    print("\n")
    return "".join(response_tokens)


def test_web_surfing() -> None:
    print("\nINICIANDO PROTOCOLO DE NAVEGACION WEB")

    model_name = os.getenv("LUCY_OLLAMA_MODEL", "llama3.1:8b")
    engine = OllamaEngine(model=model_name)

    prompt = """
OBJETIVO: Abrir Firefox y navegar a wikipedia.org.

REGLAS:
- NO expliques el plan.
- NO escribas JSON en el chat.
- SOLO USA LAS HERRAMIENTAS.

SECUENCIA OBLIGATORIA:
1. Usa perform_action con action="hotkey" y keys=["winleft"] para abrir el lanzador.
2. Usa perform_action con action="type" y text="firefox".
3. Usa perform_action con action="hotkey" y keys=["enter"].
4. Luego usa capture_screen para confirmar que Firefox abrió.
"""

    print("\n--- TURNO 1 ---")
    run_prompt(engine, prompt)

    print("Esperando 5 segundos para que la GUI responda...")
    time.sleep(5)

    prompt_2 = (
        "Toma una captura y dime si ves Firefox. "
        "Si esta abierto, escribe wikipedia.org y presiona Enter."
    )

    print("\n--- TURNO 2 ---")
    run_prompt(engine, prompt_2)


if __name__ == "__main__":
    test_web_surfing()
