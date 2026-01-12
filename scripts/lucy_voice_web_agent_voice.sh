#!/usr/bin/env bash
set -e

# Script de arranque para el agente de voz + web de Lucy

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Activar entorno virtual de Lucy voz
if [ -f ".venv-lucy-voz/bin/activate" ]; then
    # shellcheck disable=SC1091
    source ".venv-lucy-voz/bin/activate"
else
    echo "[Lucy Voz Web] No se encontró .venv-lucy-voz. Crealo antes de ejecutar este script."
    exit 1
fi

python lucy_agents/voice_web_agent.py "$@"
