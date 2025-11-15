#!/usr/bin/env python3
"""
test_asr_from_tts.py – Prueba de reconocimiento de voz (ASR) con faster-whisper
usando el archivo de prueba generado por Mimic 3 (`lucy_tts_test.wav`).

Flujo:
    texto -> TTS (Mimic 3) -> WAV -> ASR (Whisper) -> texto
"""

from pathlib import Path
from faster_whisper import WhisperModel


def main():
    base_dir = Path(__file__).resolve().parent
    audio_path = base_dir / "lucy_tts_test.wav"

    if not audio_path.exists():
        print(f"[ERROR] No se encontró el archivo de audio: {audio_path}")
        print("Generalo antes con Mimic 3.")
        return

    model_size = "small"
    print("== Prueba ASR con faster-whisper ==")
    print(f"Usando modelo: {model_size}")
    print(f"Archivo de audio: {audio_path}")

    # Carga el modelo en CPU (evitamos CUDA/cuDNN por ahora)
    model = WhisperModel(model_size, device="cpu", compute_type="int8")

    segments, info = model.transcribe(str(audio_path), language="es")

    print(f"\nIdioma detectado: {info.language} (confianza: {info.language_probability:.2f})")
    print("\nTexto reconocido:")
    for segment in segments:
        print(f"- {segment.text.strip()}")


if __name__ == "__main__":
    main()
