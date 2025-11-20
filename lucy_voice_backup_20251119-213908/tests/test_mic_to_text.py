#!/usr/bin/env python3
"""
test_mic_to_text.py – Prueba de reconocimiento de voz (ASR) con faster-whisper
usando el micrófono como fuente de audio.

Requisitos (ya están instalados en `lucy_voice/requirements.txt`):
    - sounddevice
    - numpy
    - faster-whisper

Flujo:
    1. Graba unos segundos de audio del micrófono (1 canal, 16 kHz).
    2. Guarda el audio en un archivo WAV temporal llamado
       `mic_test_input.wav` en la misma carpeta de tests.
    3. Carga el modelo Whisper “small” en CPU (`device="cpu"`,
       `compute_type="int8"`).
    4. Transcribe el archivo y muestra:
        * encabezado
        * ruta del archivo
        * idioma detectado y confianza
        * texto reconocido (una línea por segmento).
"""

import sys
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


def record_to_wav(duration_sec: float, samplerate: int = 16000) -> Path:
    """
    Graba audio desde el micrófono y devuelve la ruta del WAV temporal.
    """
    try:
        print(f"Grabando {duration_sec} segundos a {samplerate} Hz…")
        audio = sd.rec(
            int(duration_sec * samplerate),
            samplerate=samplerate,
            channels=1,
            dtype="int16",
        )
        sd.wait()
    except sd.PortAudioError as exc:
        print(f"[ERROR] No se pudo acceder al micrófono: {exc}")
        sys.exit(1)

    # Guardar en un WAV usando el módulo wave de la stdlib
    wav_path = Path(__file__).resolve().parent / "mic_test_input.wav"
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)  # 16-bit -> 2 bytes
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())
    return wav_path


def transcribe_audio(audio_path: Path):
    """
    Usa faster-whisper para transcribir el archivo WAV.
    Devuelve los segmentos y el objeto de información (`info`).
    """
    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, info = model.transcribe(str(audio_path), language="es")
    return segments, info


def main() -> None:
    """
    Ejecuta la prueba completa: grabación → guardado → ASR → salida.
    """
    duration = 5  # segundos
    wav_path = record_to_wav(duration)

    print("\n== Prueba ASR desde micrófono ==")
    print(f"Archivo de audio: {wav_path}")

    try:
        segments, info = transcribe_audio(wav_path)
    except Exception as exc:
        print(f"[ERROR] Falló la transcripción: {exc}")
        return

    print(f"\nIdioma detectado: {info.language} (confianza: {info.language_probability:.2f})")
    print("\nTexto reconocido:")
    for seg in segments:
        text = seg.text.strip()
        if text:
            print(f"- {text}")


if __name__ == "__main__":
    main()
