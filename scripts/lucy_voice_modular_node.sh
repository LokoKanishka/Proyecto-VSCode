#!/usr/bin/env bash
set -euo pipefail

# Ubicar carpeta del proyecto (raíz de Proyecto-VSCode)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

cd "${PROJECT_ROOT}"

# Activar la venv de Lucy
if [[ -f "${PROJECT_ROOT}/.venv-lucy-voz/bin/activate" ]]; then
    # shellcheck disable=SC1091
    source "${PROJECT_ROOT}/.venv-lucy-voz/bin/activate"
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
