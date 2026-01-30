#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT/logs"
LOG_FILE="$LOG_DIR/voice_turns.log"
mkdir -p "$LOG_DIR"

if [ $# -lt 1 ]; then
  echo "Usage: $0 --wav path/to/file.wav"
  exit 1
fi

while [[ $# -gt 0 ]]; do
  case $1 in
    --wav)
      shift
      WAV_PATH="$1"
      ;;
    *)
      shift
      ;;
  esac
done

if [ -z "${WAV_PATH:-}" ]; then
  echo "Debe proporcionarse --wav WAV_PATH"
  exit 1
fi

source "$ROOT/.venv-lucy-voz/bin/activate"

python3 - <<'PY'
import json
import soundfile as sf
import numpy as np
from datetime import datetime
from pathlib import Path

from lucy_voice.pipeline.voice_pipeline import LucyOrchestrator

wav_path = Path("${WAV_PATH}")
assert wav_path.exists(), f"No existe {wav_path}"

data, sr = sf.read(wav_path, always_2d=False, dtype="float32")
if data.ndim > 1:
    data = data[:, 0]

orchestrator = LucyOrchestrator()
text, _lang = orchestrator.asr.transcribe(data)
response = orchestrator.llm.generate_response(text)

log_entry = {
    "timestamp": datetime.utcnow().isoformat(),
    "input": text,
    "response": response,
}

log_path = Path("${LOG_FILE}")
log_path.parent.mkdir(parents=True, exist_ok=True)
with log_path.open("a", encoding="utf-8") as f:
    f.write(json.dumps(log_entry, ensure_ascii=False))
    f.write("\\n")
print("Voice turn logged to", log_path)
PY
