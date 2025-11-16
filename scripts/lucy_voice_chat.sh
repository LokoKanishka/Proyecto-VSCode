#!/usr/bin/env bash
set -e

# Ir a la raíz del proyecto (carpeta padre de scripts/)
cd "$(dirname "$0")/.."

# Activar el entorno virtual de Lucy voz
source .venv-lucy-voz/bin/activate

# Iniciar el chat textual de Lucy
python -m lucy_voice.pipeline_lucy_voice
