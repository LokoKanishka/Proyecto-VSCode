#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo ">> Regenerando lucy_voice/wakeword_iddkd.py completo..."

cat > lucy_voice/wakeword_iddkd.py << 'EOF'
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
THRESHOLD = 0.2    # umbral base de openWakeWord (más sensible)
REQUIRED_HITS = 1  # cantidad de frames consecutivos por encima del umbral
COOLDOWN_SECONDS = 1.0  # tiempo mínimo entre activaciones válidas


def _listen_for_wake_word(model: Model, logger: logging.Logger) -> None:
    """Bloquea hasta detectar el wake word usando openWakeWord."""
    logger.info(
        "Esperando wake word (openWakeWord, frame=%d, threshold=%.2f)...",
        FRAME_SIZE,
        THRESHOLD,
    )

    # Usamos float32 en [-1, 1], que es lo que espera openWakeWord
    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SIZE,
    ) as stream:
        consecutive_hits = 0
        last_detection_time = 0.0

        while True:
            audio, _ = stream.read(FRAME_SIZE)
            if audio.size == 0:
                continue

            # audio: shape (FRAME_SIZE, 1) float32 → 1D
            audio_f32 = audio.reshape(-1).astype(np.float32)

            prediction = model.predict(audio_f32)

            # Nos quedamos con el score del modelo 'hey_jarvis'
            score = float(prediction.get("hey_jarvis", 0.0))

            logger.debug("OWW prediction=%r score=%.3f", prediction, score)

            if score >= THRESHOLD:
                consecutive_hits += 1
            else:
                consecutive_hits = 0

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
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )
    logger = logging.getLogger("LucyWakeWord")

    logger.info("Iniciando detección de wake word con openWakeWord...")
    logger.info(
        "Decí algo como 'hey jarvis' cerca del micrófono para activar a Lucy."
    )

    # Instanciamos el modelo de wake word para 'hey_jarvis'
    # Si el modelo no está presente, openWakeWord intentará descargarlo.
    oww_model = Model(wakeword_models=["hey_jarvis"])

    # Pipeline de Lucy (ASR + LLM + TTS)
    pipeline = LucyVoicePipeline(LucyPipelineConfig())

    try:
        while True:
            _listen_for_wake_word(oww_model, logger)

            logger.info("Wake word detectada. Iniciando roundtrip de Lucy...")
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
EOF

echo ">> Listo: wakeword_iddkd.py regenerado."
