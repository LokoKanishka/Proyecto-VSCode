#!/usr/bin/env python
"""
Lucy Voice Web Agent (loop manos libres + web sólo por comando)

Comportamiento:

- Presionás Enter UNA sola vez para empezar.
- Lucy entra en un loop de frames (~5 s) con:

    [Lucy Voz Web] Escuchando (5 s)…

- Si decís algo como:
    "busca en web la economia argentina"
    "lucy busca en la web inflacion argentina"
  → Usa lucy_agents.web_agent.run_web_research(query)
    → Muestra el texto en pantalla
    → NO lo lee por defecto.
    → Si en la MISMA frase decís también "leelo / lee la respuesta",
      lo lee también con Mimic3.

- Si decís:
    "lee la respuesta", "leelo", "lucy lee"
  → Lee en voz alta la última respuesta (sea web o chat).

- Para el resto de frases (sin "busca en web" ni "lee…"):
  → Se comporta "normal":
     - llama a un modelo local de Ollama (gpt-oss:20b por defecto),
       como chat de Lucy.
     - imprime la respuesta en pantalla.
     - NO la lee automáticamente (solo por comando de lectura).

- Para terminar por voz:
    "lucy dormi", "lucy dormite", "dormi", "dormite".
- Para cortar todo de golpe: Ctrl+C en la terminal.
"""

from __future__ import annotations

import os
import sys
import shlex
import subprocess
import textwrap
import re
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import sounddevice as sd
import whisper
from unidecode import unidecode
import ollama

# Aseguramos que el proyecto raíz esté en sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(os.path.join(__file__, "..")))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from lucy_agents.web_agent import run_web_research, DEFAULT_OLLAMA_MODEL_ID  # noqa: E402


SAMPLE_RATE = 16000
CHANNELS = 1
FRAME_SECONDS = 5  # duración del frame de escucha

DEFAULT_VOICE_ID = os.getenv("LUCY_VOICE_TTS_VOICE", "es_ES/m-ailabs_low")
DEFAULT_CHAT_MODEL_ID = os.getenv("LUCY_VOICE_OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL_ID)


def normalize_text(text: str) -> str:
    """Normaliza texto para detección de comandos.

    - pasa a minúsculas
    - saca tildes
    - borra puntuación (comas, puntos, signos, etc.)
    """
    text = text.lower()
    text = unidecode(text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def is_sleep_command(norm_text: str) -> bool:
    """Detecta 'lucy dormi', 'lucy dormite', 'dormi', 'dormite'."""
    triggers = [
        "lucy dormi",
        "lucy dormite",
        "dormi",
        "dormite",
    ]
    return any(t in norm_text for t in triggers)


def is_read_command(norm_text: str) -> bool:
    """Detecta comandos tipo 'lee la respuesta', 'leelo', 'lucy lee'."""
    triggers = [
        "lee la respuesta",
        "lee la anterior",
        "lee el texto",
        "lee eso",
        "lee",
        "leelo",
        "leelo lucy",
        "lucy lee",
        "lucy leelo",
    ]
    return any(t in norm_text for t in triggers)


def extract_web_query(norm_text: str, original_text: str) -> Optional[Tuple[str, bool]]:
    """Detecta comando de búsqueda web y extrae la query.

    Reconoce cosas tipo:
      "busca en web ..."
      "busca en la web ..."
      "busca en internet ..."
      "lucy busca en web ..."

    Devuelve:
        (query, quiere_lectura)
    o None si no hay comando de web.
    """
    web_triggers = [
        "busca en web",
        "busca en la web",
        "busca en internet",
        "busca en la red",
        "lucy busca en web",
        "lucy busca en la web",
        "lucy busca en internet",
        "lucy busca en la red",
    ]

    wants_read = is_read_command(norm_text)

    for trig in web_triggers:
        idx = norm_text.find(trig)
        if idx != -1:
            start = idx + len(trig)
            # usamos el texto original desde ese punto para conservar mayúsculas
            query = original_text[start:].strip()
            if not query:
                query = original_text.strip()
            return query, wants_read

    return None


def record_frame(seconds: int = FRAME_SECONDS) -> np.ndarray:
    """Graba un frame corto de audio (loop manos libres)."""
    print(f"[Lucy Voz Web] Escuchando ({seconds} s)…")
    audio = sd.rec(
        int(seconds * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()
    if audio.ndim > 1:
        audio = audio[:, 0]
    return audio


def load_whisper_model() -> "whisper.Whisper":
    model_id = os.getenv("LUCY_WEB_WHISPER_MODEL", "small")
    print(f"[Lucy Voz Web] Cargando modelo Whisper: {model_id} (puede tardar la primera vez)…")
    model = whisper.load_model(model_id)
    return model


def transcribe_audio(model: "whisper.Whisper", audio: np.ndarray) -> str:
    result = model.transcribe(audio, language="es", fp16=False)
    text = (result.get("text") or "").strip()
    return text


def speak_with_mimic3(text: str, voice: str = DEFAULT_VOICE_ID) -> None:
    """Lee el texto usando mimic3 + aplay, si están disponibles."""
    text = text.strip()
    if not text:
        return

    if os.getenv("LUCY_WEB_AGENT_MUTE", "").lower() in {"1", "true", "yes"}:
        print("[Lucy Voz Web] LUCY_WEB_AGENT_MUTE=1, no se reproduce audio.")
        return

    from shutil import which

    if which("mimic3") is None or which("aplay") is None:
        print("[Lucy Voz Web] mimic3 o aplay no están disponibles; muestro sólo texto.")
        return

    text_for_tts = textwrap.fill(text, width=120)
    cmd = f"mimic3 --voice {shlex.quote(voice)} {shlex.quote(text_for_tts)} | aplay -q"

    try:
        subprocess.run(cmd, shell=True, check=False)
    except KeyboardInterrupt:
        print("\n[Lucy Voz Web] Reproducción interrumpida por el usuario.")
    except Exception as exc:
        print(f"[Lucy Voz Web] Error al usar mimic3: {exc}")


def chat_with_llm(
    history: List[Dict[str, str]],
    user_text: str,
    model_id: Optional[str] = None,
) -> str:
    """Chat simple con Ollama usando historial en memoria."""
    model_name = model_id or DEFAULT_CHAT_MODEL_ID

    messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                "Sos Lucy, un asistente de voz local en español rioplatense. "
                "Respondés de forma clara, cercana y precisa, sin inventar datos concretos. "
                "Estás corriendo en la máquina de Diego de forma local."
            ),
        },
        *history,
        {"role": "user", "content": user_text},
    ]

    resp = ollama.chat(model=model_name, messages=messages)
    answer = (resp.get("message", {}).get("content") or "").strip()

    history.append({"role": "user", "content": user_text})
    history.append({"role": "assistant", "content": answer})

    return answer


def main() -> None:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(" Lucy Voice Web Agent (loop manos libres)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"STT: Whisper (modelo local)")
    print(f"Chat LLM: Ollama ({DEFAULT_CHAT_MODEL_ID})")
    print("Web Agent: lucy_agents.web_agent (DDGS + Ollama)")
    print("TTS: Mimic3 (solo si se lo pedís por voz)")
    print("")
    print("Instrucciones:")
    print("  - Presioná Enter una sola vez para empezar a hablar.")
    print("  - Para buscar en la web, decí algo como:")
    print("       «busca en web la economia argentina»")
    print("       «lucy busca en la web inflacion argentina»")
    print("  - Para que lea en voz alta la última respuesta (web o chat), decí:")
    print("       «lee la respuesta», «leelo», «lucy lee»")
    print("  - Para que se duerma, podés decir «lucy dormi» o «dormite lucy».")
    print("  - Ctrl+C corta el programa.\n")

    model = load_whisper_model()

    try:
        input("Presioná Enter para comenzar el loop de escucha manos libres… ")
    except (EOFError, KeyboardInterrupt):
        print("\n[Lucy Voz Web] Sesión cancelada antes de empezar.")
        return

    print("\n[Lucy Voz Web] Empezamos. Habla cuando quieras. Ctrl+C para terminar.\n")

    last_answer: str = ""
    chat_history: List[Dict[str, str]] = []

    while True:
        try:
            audio = record_frame()
        except KeyboardInterrupt:
            print("\n[Lucy Voz Web] Sesión finalizada por el usuario.")
            break
        except Exception as exc:
            print(f"[Lucy Voz Web] Error al grabar audio: {exc}")
            continue

        try:
            transcript = transcribe_audio(model, audio)
        except Exception as exc:
            print(f"[Lucy Voz Web] Error al transcribir el audio: {exc}")
            continue

        if not transcript.strip():
            # nada entendido en este frame, seguimos escuchando
            continue

        print(f"\nYou (voz): {transcript}\n")
        norm = normalize_text(transcript)

        # Dormir
        if is_sleep_command(norm):
            print("[Lucy Voz Web] Recibí la orden de dormir. Cierro la sesión.")
            break

        # ¿Comando de web?
        web_cmd = extract_web_query(norm, transcript)
        if web_cmd is not None:
            query, wants_read = web_cmd
            print(f"[Lucy Voz Web] Ejecutando búsqueda web para: {query!r}\n")
            try:
                answer = run_web_research(task=query, model_id=None, max_results=8, verbosity=1)
            except Exception as exc:
                print(f"[Lucy Voz Web] Error al ejecutar el agente web: {exc}")
                continue

            last_answer = answer

            print("──────── Respuesta de Lucy Web ────────\n")
            print(answer)
            print("\n───────────────────────────────────────\n")

            if wants_read:
                print("[Lucy Voz Web] Leyendo en voz alta la respuesta web…")
                speak_with_mimic3(last_answer)

            continue

        # ¿Comando de lectura sin búsqueda?
        if is_read_command(norm):
            if last_answer.strip():
                print("[Lucy Voz Web] Leyendo en voz alta la última respuesta…")
                speak_with_mimic3(last_answer)
            else:
                print("[Lucy Voz Web] Todavía no hay ninguna respuesta para leer.")
            continue

        # Caso normal: chat con el modelo local (sin web)
        print("[Lucy Voz Web] Mensaje normal: respondo con el modelo local (sin web)…\n")
        try:
            answer = chat_with_llm(chat_history, transcript, model_id=None)
        except Exception as exc:
            print(f"[Lucy Voz Web] Error al consultar el modelo local: {exc}")
            continue

        last_answer = answer

        print("──────── Respuesta de Lucy (chat local) ────────\n")
        print(answer)
        print("\n───────────────────────────────────────────────\n")
        # No se lee en voz alta automáticamente: solo por comando "lee…"


if __name__ == "__main__":
    main()
