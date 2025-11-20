#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo ">> Regenerando lucy_voice/wakeword_iddkd.py con umbral dinámico..."

cat > lucy_voice/wakeword_iddkd.py << 'PYEOF'
from __future__ import annotations

import logging
import time

from typing import List

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

from .pipeline_lucy_voice import LucyPipelineConfig, LucyVoicePipeline

# Audio / wake word
SAMPLE_RATE = 16000
FRAME_SIZE = 1280           # ~80 ms a 16 kHz
BASELINE_SECONDS = 3.0      # tiempo inicial de silencio para calibrar
REQUIRED_HITS = 5           # frames consecutivos por encima del umbral
COOLDOWN_SECONDS = 1.5      # mínimo entre activaciones válidas
MIN_ABS_THRESHOLD = 1e-5    # umbral mínimo absoluto


def _predict_score(model: Model, audio_block: np.ndarray, logger: logging.Logger) -> float:
    """Devuelve el score del modelo 'hey_jarvis' para un bloque de audio."""
    if audio_block.size == 0:
        return 0.0

    # sounddevice entrega (FRAME_SIZE, 1) → 1D float32
    audio_f32 = audio_block.reshape(-1).astype(np.float32)
    prediction = model.predict(audio_f32)

    score = float(prediction.get("hey_jarvis", 0.0))
    logger.debug("OWW prediction=%r score=%.7f", prediction, score)
    return score


def _calibrate_baseline(model: Model, logger: logging.Logger) -> float:
    """Mide el ruido de fondo para fijar un umbral dinámico."""
    logger.info(
        "Calibrando wake word: mantené SILENCIO durante %.1f segundos...",
        BASELINE_SECONDS,
    )

    scores: List[float] = []

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SIZE,
    ) as stream:
        num_frames = int(BASELINE_SECONDS * SAMPLE_RATE / FRAME_SIZE)
        for i in range(num_frames):
            audio, _ = stream.read(FRAME_SIZE)
            s = _predict_score(model, audio, logger)
            scores.append(s)

    if not scores:
        logger.warning(
            "No se obtuvieron muestras de baseline, usando umbral mínimo fijo."
        )
        return MIN_ABS_THRESHOLD

    mean = float(np.mean(scores))
    std = float(np.std(scores))

    # Umbral = media + 5*desvío, pero nunca menor que MIN_ABS_THRESHOLD
    threshold = max(mean + 5.0 * std, MIN_ABS_THRESHOLD)

    logger.info(
        "Baseline wake word: mean=%.7g std=%.7g ⇒ threshold=%.7g",
        mean,
        std,
        threshold,
    )
    return threshold


def _listen_for_wake_word(model: Model, threshold: float, logger: logging.Logger) -> None:
    """Bloquea hasta detectar el wake word según el umbral dado."""
    logger.info(
        "Esperando wake word ('hey jarvis') "
        "(threshold dinámico=%.7g, hits=%d)...",
        threshold,
        REQUIRED_HITS,
    )

    consecutive_hits = 0
    last_detection_time = 0.0

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SIZE,
    ) as stream:
        while True:
            audio, _ = stream.read(FRAME_SIZE)
            score = _predict_score(model, audio, logger)

            if score >= threshold:
                consecutive_hits += 1
            else:
                consecutive_hits = 0

            if consecutive_hits >= REQUIRED_HITS:
                now = time.time()
                if now - last_detection_time >= COOLDOWN_SECONDS:
                    logger.info(
                        "Wake word detectada (score=%.7f, hits=%d).",
                        score,
                        consecutive_hits,
                    )
                    last_detection_time = now
                    return
                else:
                    logger.debug(
                        "Wake word en cooldown (%.2fs), ignorando.",
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
        "Primero calibramos el ruido de fondo. No hables hasta que termine la calibración."
    )

    # Modelo general de openWakeWord (carga todos los wake words conocidos)
    oww_model = Model()

    # 1) Calibrar umbral dinámico para 'hey_jarvis'
    threshold = _calibrate_baseline(oww_model, logger)

    # 2) Crear pipeline de Lucy (ASR + LLM + TTS)
    pipeline = LucyVoicePipeline(LucyPipelineConfig())

    try:
        while True:
            # 3) Esperar wake word con el umbral calculado
            _listen_for_wake_word(oww_model, threshold, logger)

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
PYEOF

echo ">> Listo: wakeword_iddkd.py regenerado con umbral dinámico."
