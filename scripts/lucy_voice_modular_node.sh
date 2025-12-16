#!/usr/bin/env bash
set -euo pipefail

# Ubicar carpeta del proyecto (raíz de Proyecto-VSCode)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export LUCY_LOG_DIR="${LUCY_LOG_DIR:-$PROJECT_ROOT/logs}"

cd "${PROJECT_ROOT}"

# Activar la venv de Lucy
if [[ -f "${PROJECT_ROOT}/.venv-lucy-voz/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.venv-lucy-voz/bin/activate"
    export PATH="$PROJECT_ROOT/scripts/bin:$PATH"

if [[ "${1:-}" == "--check-env" ]]; then
  echo "mimic3 -> $(command -v mimic3)"
  echo "LUCY_LOG_DIR -> ${LUCY_LOG_DIR}"
  rm -f "$LUCY_LOG_DIR/mimic3.log" /tmp/lucy_env_check.wav
  set +e
  echo "prueba check-env" | mimic3 --stdout > /tmp/lucy_env_check.wav
  RC=$?
  set -e
  echo "rc=$RC"
  echo "=== tail mimic3.log ==="
  tail -n 3 "$LUCY_LOG_DIR/mimic3.log" || echo "NO log"
  echo "=== wav ==="
  ls -lh /tmp/lucy_env_check.wav || true
  exit 0
fi
else
    echo "[ERROR] No se encontró .venv-lucy-voz en ${PROJECT_ROOT}" >&2
    exit 1
fi

# Ir al submódulo del nodo de voz modular
NODE_DIR="${PROJECT_ROOT}/external/nodo-de-voz-modular-de-lucy"
if [[ ! -d "${NODE_DIR}" ]]; then
    echo "[ERROR] No se encontró el submódulo nodo-de-voz-modular-de-lucy en ${NODE_DIR}" >&2
    exit 1
fi

cd "${NODE_DIR}"

echo "[Lucy modular] Lanzando nodo de voz modular (app.py) con CUDA_VISIBLE_DEVICES=\"\"..."
CUDA_VISIBLE_DEVICES="" python app.py
