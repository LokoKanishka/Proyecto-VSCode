from __future__ import annotations

import logging
import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

from .pipeline_lucy_voice import LucyPipelineConfig, LucyVoicePipeline

# Parámetros de audio / wake word
SAMPLE_RATE = 16000
FRAME_SIZE = 1280  # 80 ms a 16 kHz
THRESHOLD = 0.5    # umbral base de openWakeWord
REQUIRED_HITS = 3  # cantidad de frames consecutivos por encima del umbral
COOLDOWN_SECONDS = 1.0  # tiempo mínimo entre activaciones válidas


def _listen_for_wake_word(model: Model, logger: logging.Logger) -> None:
    """Bloquea hasta detectar el wake word usando openWakeWord."""
    logger.info(
        "Esperando wake word (openWakeWord, frame=%d, threshold=%.2f)...",
        FRAME_SIZE,
        THRESHOLD,
    )

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME_SIZE,
    ) as stream:
        consecutive_hits = 0
        last_detection_time = 0.0

        while True:
            audio, _ = stream.read(FRAME_SIZE)
            if audio.size == 0:
                continue

            # audio: shape (FRAME_SIZE, 1) int16 → 1D
            audio_int16 = audio.reshape(-1)

            prediction = model.predict(audio_int16)

            # Intentamos primero claves típicas de OWW; como fallback usamos el máximo
            score_jarvis = max(
                float(prediction.get("hey_jarvis", 0.0)),
                float(prediction.get("hey jarvis", 0.0)),
            )
            score = score_jarvis if score_jarvis > 0.0 else float(
                max(prediction.values()) if prediction else 0.0
            )

            logger.debug("OWW score=%.3f", score)

            if score >= THRESHOLD:
                consecutive_hits += 1
            else:
                consecutive_hits = max(0, consecutive_hits - 1)

            if consecutive_hits >= REQUIRED_HITS:
                now = time.time()
                if now - last_detection_time >= COOLDOWN_SECONDS:
                    logger.info(
                        "Wake word detectada (score=%.3f, hits=%d).",
                        score,
                        consecutive_hits,
                    )
                    last_detection_time = now
                    return
                else:
                    logger.debug(
                        "Wake word en cooldown (%.2fs)...",
                        now - last_detection_time,
                    )
                    consecutive_hits = 0


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )
    logger = logging.getLogger("LucyWakeWord")

    logger.info("Iniciando detección de wake word con openWakeWord...")
    logger.info(
        "Decí algo como 'hey jarvis' cerca del micrófono para activar a Lucy."
    )

    # Instanciamos el modelo de wake word (uso default de OWW)
    oww_model = Model(inference_framework="onnx")

    # Pipeline de Lucy (ASR + LLM + TTS)
    pipeline = LucyVoicePipeline(LucyPipelineConfig())

    try:
        while True:
            _listen_for_wake_word(oww_model, logger)

            logger.info("Wake word detectada. Iniciando roundtrip de Lucy...")
            # IMPORTANTE: ahora respetamos el valor de retorno
            should_stop = pipeline.run_mic_llm_roundtrip_once(duration_sec=5.0)

            if should_stop:
                logger.info(
                    "Lucy pidió apagarse (comando de voz). "
                    "Saliendo del modo wake word."
                )
                break

            logger.info(
                "Roundtrip finalizado. Volviendo a escuchar el wake word..."
            )

    except KeyboardInterrupt:
        logger.info("Interrupción por teclado (Ctrl+C). Saliendo.")


if __name__ == "__main__":
    main()
