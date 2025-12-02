#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [[ ! -d ".venv-lucy-voz" ]]; then
  echo "[Lucy web-agent] ERROR: no se encontró .venv-lucy-voz en ${PROJECT_ROOT}" >&2
  exit 1
fi

# Activar entorno virtual
# shellcheck disable=SC1091
source ".venv-lucy-voz/bin/activate"

python "scripts/lucy_web_agent_cli.py" "$@"
