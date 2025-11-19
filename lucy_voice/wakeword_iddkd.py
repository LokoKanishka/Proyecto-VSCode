#!/usr/bin/env python3
"""
Loop de detección de wake word para Lucy usando openWakeWord.

Por ahora usamos el modelo pre-entrenado "hey jarvis" como placeholder
del futuro wake word personalizado "iddkd".
"""

import logging
import queue
import sys
import time

import numpy as np
import sounddevice as sd

from openwakeword.model import Model

SAMPLE_RATE = 16000
BLOCKSIZE = 1280  # 80 ms a 16 kHz
THRESHOLD = 0.05  # umbral de activación (MUCHO más sensible para debug)


log = logging.getLogger("LucyWakeWord")


def _setup_model() -> Model:
    """
    Inicializa el modelo de openWakeWord.

    Usamos la inicialización por defecto (sin argumentos), igual que en los tests
    de Fase 1. Eso carga los modelos de wake word que ya tenga disponible la
    instalación de openWakeWord (por ejemplo "hey_jarvis", "ok_nabu", etc.).
    """
    model = Model()
    try:
        # En algunas versiones de openwakeword existe este atributo,
        # en otras no; por eso lo hacemos defensivo.
        available = getattr(model, "models", None)
        if available is not None:
            log.info("Wake words disponibles: %s", list(available.keys()))
    except Exception:
        # Si falla, no pasa nada: es solo info de debug.
        pass
    return model



def _audio_loop() -> None:
    """
    Loop principal: abre el micrófono, pasa audio al modelo de wake word
    y loguea cuando detecta activación.
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

            # Si supera el umbral, avisar
            if jarvis_score >= THRESHOLD:
                print(f"\n[WakeWord] Detecté 'hey_jarvis' con score={jarvis_score:.2f}")

            # Pequeña pausa para no saturar la CPU
            time.sleep(0.01)



def main() -> None:
    try:
        _audio_loop()
    except KeyboardInterrupt:
        log.info("Wake word interrumpido por teclado. Chau 💜")
        sys.exit(0)


if __name__ == "__main__":
    main()
