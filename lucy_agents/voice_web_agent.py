#!/usr/bin/env python3
"""
Lucy Voice Web Agent (loop manos libres v5)

- STT: Whisper local
- Chat LLM: Ollama (gpt-oss:20b por defecto)
- Web Agent: lucy_agents.web_agent.run_web_research (SearXNG local + fallback DDGS + Ollama)
- TTS: Mimic3 + aplay

Reglas:
- Presionás Enter una sola vez para arrancar el loop.
- Chat normal (sin pedir web):
    -> responde con texto + voz.
- Si la frase menciona "buscar" + "web/internet/google":
    -> usa el Web Agent, muestra solo texto (no voz).
- "lee la respuesta" / "leelo" / "lucy lee" / "quiero que me leas los resultados":
    -> lee por voz la última respuesta (web o chat).
- "lucy dormi" / "dormite lucy":
    -> termina el programa.
"""

import os
import sys
import subprocess
import textwrap
import shlex
from typing import Optional

import numpy as np
import sounddevice as sd
import whisper
from unidecode import unidecode
from shutil import which

# --- Aseguramos que el proyecto raíz esté en sys.path --- #

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPTS_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    import ollama
except ImportError:
    ollama = None

try:
    from lucy_agents.web_agent import run_web_research, DEFAULT_OLLAMA_MODEL_ID as WEB_DEFAULT_MODEL
except Exception as exc:
    print(f"[Lucy Voz Web] Aviso: no pude importar lucy_agents.web_agent ({exc})")
    run_web_research = None
    WEB_DEFAULT_MODEL = "qwen2.5:32b"


SAMPLE_RATE = 16000
LISTEN_SECONDS = 5

CHAT_MODEL_ID = os.environ.get("LUCY_OLLAMA_MODEL", WEB_DEFAULT_MODEL)

WEB_MODEL_ID = os.environ.get("LUCY_WEB_AGENT_OLLAMA_MODEL", WEB_DEFAULT_MODEL)

SYSTEM_PROMPT = (
    "Sos Lucy, un asistente local en la máquina de Diego. "
    "Hablás en español rioplatense, con tono cuidado y directo. "
    "Respondés de forma clara, breve y precisa, sin tratar al usuario como niño."
)


def normalize_text(text: str) -> str:
    """Pasa a minúsculas, sin tildes ni espacios múltiples."""
    return " ".join(unidecode(text.lower()).strip().split())


def is_sleep_command(text_norm: str) -> bool:
    return (
        ("lucy dormi" in text_norm)
        or ("lucy dormite" in text_norm)
        or (text_norm == "dormi")
        or (text_norm == "dormite")
    )


def is_read_command(text_norm: str) -> bool:
    """
    Detecta pedidos como:
      - lee la respuesta / lee los resultados
      - leé la respuesta de la web
      - quiero que me leas los resultados
      - leeme los resultados / leeme eso
    """

    # Frases explícitas que seguro significan "leé la última respuesta"
    explicit_patterns = [
        "lee la respuesta",
        "lee respuesta",
        "lee los resultados",
        "leer la respuesta",
        "leer los resultados",
        "leela respuesta",
        "leeme la respuesta",
        "leeme los resultados",
        "lee el texto",
        "lee eso",
        "lee todo",
        "leelo",
        "leelos",
        "lucy lee",
        "lee la anterior",
        "leeme la anterior",
        "lee la respuesta de la web",
        "lees la respuesta",
        "lees los resultados",
    ]
    if any(p in text_norm for p in explicit_patterns):
        return True

    # Heurística general: verbo de leer + referencia a respuesta/resultados/texto/web
    has_read_verb = any(
        v in text_norm
        for v in (
            "lee",
            "leer",
            "leeme",
            "lea",
            "leas",
            "lees",  # por si dice "lees esto"
        )
    )
    has_object = any(
        w in text_norm
        for w in (
            "respuesta",
            "resultados",
            "resultado",
            "texto",
            "web",
            "eso",
            "todo",
        )
    )

    return has_read_verb and has_object


def wants_web_search(text_norm: str) -> bool:
    """Devuelve True si la frase suena a 'buscar en la web'."""
    has_where = any(k in text_norm for k in ("web", "internet", "google"))
    has_verb = any(
        v in text_norm for v in ("busca", "buscá", "buscar", "buscame", "buscarme", "buscando")
    )
    return has_where and has_verb


def record_audio(seconds: float = LISTEN_SECONDS, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Graba audio mono float32 [-1, 1] durante `seconds`."""
    print(f"[Lucy Voz Web] Escuchando ({int(seconds)} s)…")
    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    return audio[:, 0]


def find_mimic3_binary() -> Optional[str]:
    """Intenta encontrar el binario de mimic3 (PATH o .venv-lucy-voz/bin)."""
    # Candidato 1: en PATH
    if which("mimic3") is not None:
        return "mimic3"

    # Candidato 2: dentro de la venv del proyecto
    venv_mimic3 = os.path.join(PROJECT_ROOT, ".venv-lucy-voz", "bin", "mimic3")
    if os.path.isfile(venv_mimic3):
        return venv_mimic3

    return None


def speak_with_mimic3(text: str, voice: str = "es_ES/m-ailabs_low#karen_savage") -> None:
    """Reproduce el texto usando mimic3 | aplay."""
    text = text.strip()
    if not text:
        return

    mimic3_bin = find_mimic3_binary()
    aplay_bin = which("aplay")

    if mimic3_bin is None or aplay_bin is None:
        print(
            "[Lucy Voz Web] Aviso: mimic3 o aplay no se encontraron en el sistema; "
            "respondo solo por texto."
        )
        return

    wrapped = textwrap.fill(text, width=120)
    cmd = f"{shlex.quote(mimic3_bin)} --voice {shlex.quote(voice)} {shlex.quote(wrapped)} | {shlex.quote(aplay_bin)} -q"

    try:
        subprocess.run(cmd, shell=True, check=False)
    except KeyboardInterrupt:
        print("[Lucy Voz Web] Reproducción interrumpida por el usuario.")
    except Exception as exc:
        print(f"[Lucy Voz Web] Error al reproducir voz: {exc}")


def chat_with_ollama(prompt: str) -> str:
    """Llama al modelo local de Ollama para chat."""
    if ollama is None:
        return "[Lucy] Error: la librería 'ollama' no está instalada en este entorno."

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        resp = ollama.chat(model=CHAT_MODEL_ID, messages=messages)
        content = (resp.get("message", {}) or {}).get("content", "")
        content = (content or "").strip()
        if not content:
            return "[Lucy] El modelo local no devolvió contenido."
        return content
    except Exception as exc:
        return f"[Lucy] Error al llamar a Ollama: {exc}"


def main() -> None:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(" Lucy Voice Web Agent (loop manos libres)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("STT: Whisper (modelo local)")
    print(f"Chat LLM: Ollama ({CHAT_MODEL_ID})")
    print("Web Agent: lucy_agents.web_agent (SearXNG local + fallback DDGS + Ollama)")
    print("TTS: Mimic3 + aplay\n")
    print("Instrucciones:")
    print("  - Presioná Enter una sola vez para empezar a hablar.")
    print("  - Para buscar en la web, decí algo como:")
    print("       «busca en web la economia argentina»")
    print("       «podés buscar bruce wayne en la web»")
    print("  - Chat normal (sin pedir web): Lucy responde con texto + voz.")
    print("  - Para leer en voz alta la última respuesta, decí:")
    print("       «lee la respuesta», «leelo», «lucy lee»,")
    print("       «quiero que me leas los resultados», etc.")
    print("  - Para dormir, decí «lucy dormi» o «dormite lucy».")
    print("  - Ctrl+C corta el programa.\n")

    print("[Lucy Voz Web] Cargando modelo Whisper: small (puede tardar la primera vez)…")
    model = whisper.load_model("small")

    last_answer: str = ""

    input("Presioná Enter para comenzar el loop de escucha manos libres… ")
    print("[Lucy Voz Web] Empezamos. Habla cuando quieras. Ctrl+C para terminar.\n")

    try:
        while True:
            # 1) Grabamos audio
            try:
                audio = record_audio()
            except Exception as exc:
                print(f"[Lucy Voz Web] Error al grabar audio: {exc}")
                continue

            # 2) Transcribimos con Whisper
            try:
                result = model.transcribe(audio, language="es", fp16=False)
                text = (result.get("text") or "").strip()
            except Exception as exc:
                print(f"[Lucy Voz Web] Error al transcribir audio: {exc}")
                continue

            if not text:
                print("[Lucy Voz Web] No se entendió nada, probá de nuevo.\n")
                continue

            print(f"\nYou (voz): {text}\n")
            norm = normalize_text(text)

            # 3) Comando de dormir
            if is_sleep_command(norm):
                print("[Lucy Voz Web] Recibí 'lucy dormi'. Me voy a dormir y cierro la sesión.")
                break

            # 4) Comando de leer última respuesta
            if is_read_command(norm):
                if last_answer.strip():
                    print("[Lucy Voz Web] Leyendo en voz alta la última respuesta…")
                    speak_with_mimic3(last_answer)
                else:
                    print("[Lucy Voz Web] Todavía no tengo ninguna respuesta para leer.")
                continue

            # 5) Comando de búsqueda web
            if wants_web_search(norm):
                if run_web_research is None:
                    print(
                        "[Lucy Voz Web] Pedido de búsqueda web, "
                        "pero lucy_agents.web_agent no está disponible."
                    )
                    continue

                task = text.strip()
                print(f"[Lucy Voz Web] Ejecutando búsqueda en la web para: {task!r}\n")
                try:
                    answer = run_web_research(
                        task=task,
                        model_id=(
                            None
                            if (
                                os.getenv("LUCY_WEB_NO_LLM", "").strip().lower()
                                in ("1", "true", "yes", "on")
                            )
                            else WEB_MODEL_ID
                        ),
                        max_results=8,
                        verbosity=1,
                    )
                except Exception as exc:
                    print(f"[Lucy Voz Web] Error al ejecutar el Web Agent: {exc}")
                    continue

                last_answer = answer if isinstance(answer, str) else str(answer)

                print("──────── Respuesta de Lucy Web ────────\n")
                print(last_answer)
                print("\n───────────────────────────────────────\n")
                # Importante: NO leer en voz alta automáticamente.
                continue

            # 6) Caso normal: chat local con voz
            print("[Lucy Voz Web] Mensaje normal: respondo con el modelo local (sin web)…\n")
            answer = chat_with_ollama(text)
            last_answer = answer

            print("──────── Respuesta de Lucy (chat local) ────────\n")
            print(answer)
            print("\n───────────────────────────────────────────────\n")

            print("[Lucy Voz Web] Leyendo en voz alta la respuesta del chat local…")
            speak_with_mimic3(answer)

    except KeyboardInterrupt:
        print("\n[Lucy Voz Web] Sesión finalizada por el usuario.")


if __name__ == "__main__":
    main()
