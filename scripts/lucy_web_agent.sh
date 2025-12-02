#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

if [ ! -d ".venv-lucy-voz" ]; then
  python3 -m venv .venv-lucy-voz
fi

# shellcheck source=/dev/null
source ".venv-lucy-voz/bin/activate"

python "scripts/lucy_web_agent_cli.py" "$@"
