#!/usr/bin/env python3
"""
Loop de detección de wake word para Lucy usando openWakeWord.

Por ahora usamos el modelo pre-entrenado "hey_jarvis" como placeholder
del futuro wake word personalizado "iddkd".

Comportamiento actual:
- Escucha el micrófono con openWakeWord.
- Muestra continuamente el score de "hey_jarvis".
- Cuando el score supera el UMBRAL durante varios bloques seguidos,
  considera que se activó el wake word.
- Cierra el stream de audio y dispara UNA ronda de Lucy Voz:
  micrófono -> ASR -> LLM local -> TTS.
"""

import logging
import queue
import sys
import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model
from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline, LucyPipelineConfig

SAMPLE_RATE = 16000
BLOCKSIZE = 1280  # ~80 ms a 16 kHz
THRESHOLD = 0.01  # umbral de activación (muy sensible, tono normal)
REQUIRED_HITS = 3  # bloques seguidos por encima del umbral

log = logging.getLogger("LucyWakeWord")


def _setup_model() -> Model:
    """
    Inicializa el modelo de openWakeWord.

    Usamos la inicialización por defecto (sin argumentos), igual que
    en los tests de Fase 1. Eso carga los modelos de wake word que ya
    tenga disponible la instalación de openWakeWord
    (ej.: "alexa", "hey_jarvis", etc.).
    """
    model = Model()
    try:
        available = getattr(model, "models", None)
        if available is not None:
            log.info("Wake words disponibles: %s", list(available.keys()))
    except Exception:
        # Si falla, no pasa nada: es solo info de debug.
        pass
    return model


def _audio_loop() -> bool:
    """
    Loop principal: abre el micrófono, pasa audio al modelo de wake word
    y devuelve True si detectó activación de "hey_jarvis".
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s: %(message)s",
    )

    log.info("Inicializando modelo de wake word (openWakeWord)…")
    model = _setup_model()

    audio_queue: "queue.Queue[np.ndarray]" = queue.Queue()

    def callback(indata, frames, time_info, status):
        # Esta función se ejecuta en hilo de audio (sounddevice)
        if status:
            log.warning("Status de audio: %s", status)
        # Copiamos el bloque para no depender del buffer interno
        audio_queue.put(indata.copy())

    detected = False
    consecutive_hits = 0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=BLOCKSIZE,
        callback=callback,
    ):
        log.info(
            "Escuchando micrófono a %d Hz, bloques de %d muestras (~80 ms). Ctrl+C para salir.",
            SAMPLE_RATE,
            BLOCKSIZE,
        )
        log.info("Decí claramente 'hey jarvis' cerca del micrófono para probar el wake word.")

        while True:
            # Esperamos al siguiente bloque de audio
            audio_block = audio_queue.get()

            # Aplanamos a vector 1D int16
            pcm = audio_block[:, 0].astype(np.int16).flatten()

            # Obtenemos predicciones del modelo: dict {nombre_modelo: score}
            prediction = model.predict(pcm)

            # Score específico del modelo "hey_jarvis" (si existe)
            jarvis_score = prediction.get("hey_jarvis", 0.0)

            # Mostrar siempre el score de hey_jarvis en la misma línea (debug)
            print(f"score hey_jarvis = {jarvis_score:.3f}", end="\r", flush=True)

            # Contar cuántos bloques seguidos están por encima del umbral
            if jarvis_score >= THRESHOLD:
                consecutive_hits += 1
            else:
                consecutive_hits = 0

            # Si tenemos suficientes bloques seguidos por encima del umbral → activamos
            if consecutive_hits >= REQUIRED_HITS:
                print(f"\n[WakeWord] Detecté 'hey_jarvis' con score={jarvis_score:.2f}")
                detected = True
                break

            # Pequeña pausa para no saturar la CPU
            time.sleep(0.01)

    # Al salir del with, el stream de audio se cierra.
    return detected


def _run_lucy_roundtrip() -> bool:
    """
    Dispara UNA ronda de Lucy Voz:
    micrófono -> ASR -> LLM local -> TTS.

    Devuelve:
        should_stop (bool): True si Lucy pidió desactivarse
        (por ejemplo, si reconoció un comando tipo "Lucy desactivate").
    """
    log.info("Disparando una ronda de Lucy Voz (mic → LLM → TTS)…")

    cfg = LucyPipelineConfig()
    pipeline = LucyVoicePipeline(cfg)

    # Construimos el grafo (hoy es un stub de Pipecat, pero deja listo el campo)
    pipeline.build_graph()

    should_stop = pipeline.run_mic_llm_roundtrip_once(duration_sec=5.0)

    log.info("Ronda de Lucy Voz terminada (should_stop=%s)", should_stop)
    return should_stop


def main() -> None:
    try:
        while True:
            # 1) Escuchar wake word
            detected = _audio_loop()
            if not detected:
                # En la práctica, solo saldría por KeyboardInterrupt
                break

            # 2) Disparar una ronda de Lucy Voz
            should_stop = _run_lucy_roundtrip()

            # 3) Si Lucy pidió desactivarse por voz, salir del loop
            if should_stop:
                log.info(
                    "Lucy pidió desactivarse (should_stop=True). "
                    "Saliendo del loop de wake word. 💜"
                )
                break

        sys.exit(0)
    except KeyboardInterrupt:
        log.info("Wake word interrumpido por teclado. Chau 💜")
        sys.exit(0)


if __name__ == "__main__":
    main()
