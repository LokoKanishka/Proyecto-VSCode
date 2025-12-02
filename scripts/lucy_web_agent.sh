#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Activar venv de Lucy Voz
# shellcheck source=/dev/null
source ".venv-lucy-voz/bin/activate"

# Ejecutar el CLI de Lucy Web Agent con todos los argumentos que lleguen
python "scripts/lucy_web_agent_cli.py" "$@"
