#!/usr/bin/env python3
"""
Lucy Voice Web Agent (loop manos libres)

- STT: Whisper local
- Chat LLM: Ollama (gpt-oss:20b)
- Web Agent: lucy_agents.web_agent.run_web_research (DDGS + Ollama)
- TTS: Mimic3

Comportamiento:
- Presionás Enter una sola vez.
- Cada turno:
    - Escucha ~5s.
    - Transcribe con Whisper.
    - Si detecta comando de dormir -> termina.
    - Si detecta comando de leer -> lee por voz la última respuesta (web o chat).
    - Si detecta comando de buscar en web -> usa Web Agent y NO lee por voz (queda en pantalla).
    - Si no hay comando especial -> responde con chat local + voz.
"""

import os
import sys
import subprocess
from typing import Optional

import sounddevice as sd
import numpy as np
import whisper
from unidecode import unidecode

try:
    import ollama  # cliente Python de Ollama
except ImportError:
    ollama = None

try:
    # run_web_research es nuestro agente de web
    from lucy_agents.web_agent import run_web_research
except ImportError:
    run_web_research = None


SAMPLE_RATE = 16000
LISTEN_SECONDS = 5
DEFAULT_OLLAMA_MODEL_ID = os.environ.get("LUCY_OLLAMA_MODEL", "gpt-oss:20b")


SYSTEM_PROMPT = (
    "Sos Lucy, un asistente local que responde en español rioplatense, "
    "de forma breve, clara y con tono cuidado (sin tratar al usuario como niño). "
    "Estás corriendo 100% en la máquina del usuario, sin internet. "
    "Cuando respondas, hacelo directamente, sin aclarar que sos un modelo de lenguaje."
)


def normalize_text(text: str) -> str:
    """Minúsculas + sin tildes, para detectar comandos por voz."""
    return unidecode(text.lower()).strip()


def is_sleep_command(text_norm: str) -> bool:
    return ("lucy dormi" in text_norm) or ("dormite lucy" in text_norm)


def is_read_command(text_norm: str) -> bool:
    keys = [
        "lee la respuesta",
        "leela respuesta",
        "lee respuesta",
        "leelo",
        "lucy lee",
        "leeme la respuesta",
        "leela",
    ]
    return any(k in text_norm for k in keys)


def extract_web_query(text: str) -> Optional[str]:
    """
    Si la frase pide "buscar en la web", devuelve la consulta.
    Acepta cosas como:
      - "busca en web la economia argentina"
      - "busca en la web inflacion argentina"
      - "podés buscar bruce wayne en la web"
      - "lucy, buscame en internet la cotizacion del dolar"
    """
    t = normalize_text(text)

    # Patrones explícitos
    patterns = [
        "busca en web",
        "busca en la web",
        "buscá en web",
        "buscá en la web",
        "buscar en web",
        "buscar en la web",
        "busca en internet",
        "buscar en internet",
        "busca en google",
        "buscar en google",
        "lucy busca en web",
        "lucy busca en la web",
    ]
    for p in patterns:
        if p in t:
            tail = t.split(p, 1)[1].strip()
            return tail or None

    # Heurística general: tiene alguna forma de "buscar" + "web/internet/google"
    if any(w in t for w in ("web", "internet", "google")) and any(
        b in t for b in ("busca", "buscar", "buscame", "buscarme")
    ):
        cleaned = t
        for w in [
            "lucy",
            "podes",
            "podés",
            "puedes",
            "por favor",
            "busca",
            "buscá",
            "buscar",
            "buscame",
            "buscarme",
            "en la web",
            "en web",
            "en internet",
            "en google",
        ]:
            cleaned = cleaned.replace(w, "")
        cleaned = " ".join(cleaned.split())
        return cleaned or None

    return None


def record_audio(seconds: float = LISTEN_SECONDS, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Graba audio mono en float32 [-1,1]."""
    print(f"[Lucy Voz Web] Escuchando ({seconds:.0f} s)…")
    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    # Devuelve vector 1D
    return audio[:, 0]


def chat_with_ollama(prompt: str, model_id: str = DEFAULT_OLLAMA_MODEL_ID) -> str:
    """Llama al modelo local de Ollama."""
    if ollama is None:
        return (
            "[Lucy] Error: la librería 'ollama' no está instalada en este entorno. "
            "Instalala en .venv-lucy-voz para usar el chat local."
        )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]
    try:
        resp = ollama.chat(model=model_id, messages=messages)
        content = resp.get("message", {}).get("content", "").strip()
        return content or "[Lucy] No obtuve contenido del modelo local."
    except Exception as e:
        return f"[Lucy] Error al llamar a Ollama: {e}"


def speak_with_mimic3(text: str) -> None:
    """Lee el texto por TTS usando mimic3."""
    text = text.strip()
    if not text:
        return

    cmd = ["mimic3", "--voice", "es_ES/m-ailabs_low"]
    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        proc.communicate(input=text.encode("utf-8"))
    except KeyboardInterrupt:
        print("[Lucy Voz Web] Reproducción interrumpida por el usuario.")
    except Exception as e:
        print(f"[Lucy Voz Web] Error al reproducir voz: {e}")


def main() -> None:
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(" Lucy Voice Web Agent (loop manos libres)")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("STT: Whisper (modelo local)")
    print(f"Chat LLM: Ollama ({DEFAULT_OLLAMA_MODEL_ID})")
    print("Web Agent: lucy_agents.web_agent (DDGS + Ollama)")
    print("TTS: Mimic3\n")
    print("Instrucciones:")
    print("  - Presioná Enter una sola vez para empezar a hablar.")
    print("  - Para buscar en la web, decí algo como:")
    print("       «busca en web la economia argentina»")
    print("       «podés buscar bruce wayne en la web»")
    print("  - Chat normal (sin 'buscar en web'): Lucy responde con texto + voz.")
    print("  - Para que lea en voz alta la última respuesta (web o chat), decí:")
    print("       «lee la respuesta», «leelo», «lucy lee»")
    print("  - Para que se duerma, podés decir «lucy dormi» o «dormite lucy».")
    print("  - Ctrl+C corta el programa.\n")

    print("[Lucy Voz Web] Cargando modelo Whisper: small (puede tardar la primera vez)…")
    model = whisper.load_model("small")

    last_answer: str = ""

    input("Presioná Enter para comenzar el loop de escucha manos libres… ")
    print("[Lucy Voz Web] Empezamos. Habla cuando quieras. Ctrl+C para terminar.\n")

    try:
        while True:
            audio = record_audio()
            # Transcribimos audio con Whisper
            try:
                result = model.transcribe(audio, fp16=False, language="es")
                text = (result.get("text") or "").strip()
            except Exception as e:
                print(f"[Lucy Voz Web] Error al transcribir audio: {e}")
                continue

            if not text:
                print("[Lucy Voz Web] No se entendió nada, probá de nuevo.\n")
                continue

            print(f"\nYou (voz): {text}\n")
            norm = normalize_text(text)

            # 1) Comando de dormir
            if is_sleep_command(norm):
                print("[Lucy Voz Web] Recibí 'lucy dormi'. Me voy a dormir y cierro la sesión.")
                break

            # 2) Comando de lectura de última respuesta
            if is_read_command(norm):
                if last_answer.strip():
                    print("[Lucy Voz Web] Leyendo en voz alta la última respuesta…")
                    speak_with_mimic3(last_answer)
                else:
                    print("[Lucy Voz Web] Todavía no tengo ninguna respuesta para leer.")
                continue

            # 3) Comando de búsqueda en la web
            web_query = extract_web_query(text)
            if web_query:
                if run_web_research is None:
                    print("[Lucy Voz Web] Error: el módulo lucy_agents.web_agent no está disponible.")
                    continue

                print(f"[Lucy Voz Web] Buscando en la web: {web_query!r}…\n")
                try:
                    answer = run_web_research(
                        task=web_query,
                        model_id=DEFAULT_OLLAMA_MODEL_ID,
                    )
                except Exception as e:
                    print(f"[Lucy Voz Web] Error al ejecutar el Web Agent: {e}")
                    continue

                last_answer = answer if isinstance(answer, str) else str(answer)

                print("──────── Respuesta de Lucy Web ────────\n")
                print(last_answer)
                print("\n───────────────────────────────────────\n")
                # IMPORTANTE: NO leer en voz alta automáticamente.
                # Solo se leerá si luego el usuario dice "lee la respuesta".
                continue

            # 4) Caso normal: chat local con voz
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
