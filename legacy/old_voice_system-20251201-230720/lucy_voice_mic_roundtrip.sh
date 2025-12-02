#!/usr/bin/env bash
set -e

# Ir a la raíz del proyecto (carpeta padre de scripts/)
cd "$(dirname "$0")/.."

# Activar el entorno virtual de Lucy voz
source .venv-lucy-voz/bin/activate

# Ejecutar un roundtrip de voz → ASR → LLM una sola vez
python -c "from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline; p = LucyVoicePipeline(); p.run_mic_llm_roundtrip_once()"
