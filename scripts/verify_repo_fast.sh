#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT/.venv-lucy-voz/bin/activate" ]]; then
  source "$ROOT/.venv-lucy-voz/bin/activate"
fi

echo "== VERIFY REPO FAST =="

echo "[1/3] Compiling python..."
python3 -m compileall -q "$ROOT"

echo "[2/3] Running unit tests..."
# We run from ROOT to insure imports work
cd "$ROOT"
python3 -m unittest discover -s tests -p "test_*.py" -q

echo "[3/3] Validating config..."
"$ROOT/scripts/validate_config.sh"

echo "== OK =="
