#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo ">> Regenerando lucy_voice/wakeword_iddkd.py con detector SIMPLE de voz (sin openWakeWord)..."

cat > lucy_voice/wakeword_iddkd.py << 'PYEOF'
from __future__ import annotations

import logging
import time
from typing import List

import numpy as np
import sounddevice as sd

from .pipeline_lucy_voice import LucyPipelineConfig, LucyVoicePipeline

# Parámetros de audio y VAD simple
SAMPLE_RATE = 16000
FRAME_SIZE = 1024            # ~64 ms
CALIBRATION_SECONDS = 2.0    # tiempo de silencio para medir ruido
MIN_ABS_THRESHOLD = 1e-4     # umbral mínimo absoluto de energía
ENERGY_MULTIPLIER = 6.0      # cuántos desvíos estándar por encima del ruido
HITS_REQUIRED = 8            # frames consecutivos por encima del umbral
COOLDOWN_SECONDS = 1.5       # tiempo mínimo entre activaciones


def _frame_energy(block: np.ndarray) -> float:
    """Calcula energía RMS de un bloque de audio."""
    if block.size == 0:
        return 0.0
    audio = block.reshape(-1).astype(np.float32)
    return float(np.sqrt(np.mean(audio ** 2)))


def _calibrate_energy(logger: logging.Logger) -> float:
    """Mide el ruido de fondo y fija un umbral dinámico de energía."""
    logger.info(
        "Calibrando detector de voz: mantené SILENCIO durante %.1f segundos...",
        CALIBRATION_SECONDS,
    )

    energies: List[float] = []

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
        blocksize=FRAME_SIZE,
    ) as stream:
        num_frames = int(CALIBRATION_SECONDS * SAMPLE_RATE / FRAME_SIZE)
        for _ in range(num_frames):
            audio, _ = stream.read(FRAME_SIZE)
            e = _frame_energy(audio)
            energies.append(e)

    if not energies:
        logger.warning(
            "No se obtuvieron muestras de baseline, usando umbral mínimo fijo."
        )
        return MIN_ABS_THRESHOLD

    mean = float(np.mean(energies))
    std = float(np.std(energies))

    threshold = max(mean + ENERGY_MULTIPLIER * std, MIN_ABS_THRESHOLD)

    logger.info(
        "Baseline energía: mean=%.7g std=%.7g ⇒ umbral=%.7g",
        mean,
        std,
        threshold,
    )
    return threshold


def _listen_for_voice(threshold: float, logger: logging.Logger) -> None:
    """
    Espera hasta detectar voz por encima del umbral de energía.
    No distingue palabras: cualquier voz suficientemente fuerte activa a Lucy.
    """
    logger.info(
        "Esperando VOZ por encima del umbral (energía=%.7g, hits=%d)...",
        threshold,
        HITS_REQUIRED,
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
            energy = _frame_energy(audio)
            logger.debug(
                "VAD energía=%.7f (umbral=%.7f)", energy, threshold
            )

            if energy >= threshold:
                consecutive_hits += 1
            else:
                consecutive_hits = 0

            if consecutive_hits >= HITS_REQUIRED:
                now = time.time()
                if now - last_detection_time >= COOLDOWN_SECONDS:
                    logger.info(
                        "Voz detectada (energía=%.7f, hits=%d).",
                        energy,
                        consecutive_hits,
                    )
                    last_detection_time = now
                    return
                else:
                    logger.debug(
                        "Detección en cooldown (%.2fs), ignorando.",
                        now - last_detection_time,
                    )
                    consecutive_hits = 0


def main() -> None:
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )
    logger = logging.getLogger("LucyWakeWordSimple")

    logger.info(
        "Iniciando modo wake word SIMPLE (detección de voz, sin openWakeWord)..."
    )

    # 1) Calibrar ruido de fondo para fijar umbral de energía
    energy_threshold = _calibrate_energy(logger)

    # 2) Crear pipeline de Lucy (ASR + LLM + TTS)
    pipeline = LucyVoicePipeline(LucyPipelineConfig())

    try:
        while True:
            # 3) Esperar voz por encima del umbral dinámico
            _listen_for_voice(energy_threshold, logger)

            logger.info("Voz detectada. Iniciando roundtrip de Lucy...")
            should_stop = pipeline.run_mic_llm_roundtrip_once(duration_sec=5.0)

            if should_stop:
                logger.info(
                    "Lucy pidió apagarse (comando de voz). "
                    "Saliendo del modo wake word."
                )
                break

            logger.info(
                "Roundtrip finalizado. Volviendo a escuchar voz..."
            )

    except KeyboardInterrupt:
        logger.info("Interrupción por teclado (Ctrl+C). Saliendo.")


if __name__ == "__main__":
    main()
PYEOF

echo ">> Listo: wakeword_iddkd.py regenerado con detector simple de voz."
