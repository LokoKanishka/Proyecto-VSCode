#!/usr/bin/env bash
set -e

# Ir a la raíz del proyecto (carpeta padre de scripts/)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Activar el entorno virtual de Lucy voz
source .venv-lucy-voz/bin/activate

# Lanzar Lucy voz en modo push-to-talk
python -m lucy_voice.voice_chat_loop
