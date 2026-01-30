#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "🛠 Verificando pipeline de voz..."
source "$ROOT_DIR/.venv-lucy-voz/bin/activate"

python3 - <<'PY'
import logging
import os
import sys
import importlib

sys.path.insert(0, os.getcwd())

from lucy_voice.pipeline.voice_pipeline import LucyOrchestrator

log = logging.getLogger("voice_check")
log.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stdout)
log.addHandler(handler)

try:
    orchestrator = LucyOrchestrator()
    log.info("Orchestrador inicializado.")
    log.info("ASR model: %s", orchestrator.config.whisper_model_name)
    log.info("TTS voice: %s", orchestrator.config.tts_voice)
    for pkg in ("sounddevice", "soundfile", "webrtcvad", "pyautogui"):
        spec = importlib.util.find_spec(pkg)
        log.info("Dependency %s: %s", pkg, "found" if spec else "missing")
except Exception as exc:
    log.error("Fallo al inicializar: %s", exc)
    raise
PY

echo "✔ Pipeline de voz listo."
