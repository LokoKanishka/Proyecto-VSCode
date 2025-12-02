#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Activar venv de Lucy Voz
# shellcheck source=/dev/null
source ".venv-lucy-voz/bin/activate"

python "scripts/lucy_voice_web_agent_voice.py"
