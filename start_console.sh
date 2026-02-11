#!/bin/bash
set -e

# Navbar color for user clarity
echo -e "\033[1;35m💜 LUCY V1.0 - CONSOLE LAUNCHER\033[0m"

# 1. Resolve Root Directory
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${ROOT_DIR}"

# 2. Activate Virtual Environment
if [ -f ".venv/bin/activate" ]; then
    echo "⚡ Activando entorno virtual..."
    source .venv/bin/activate
elif [ -f ".venv-lucy/bin/activate" ]; then
    source .venv-lucy/bin/activate
else
    echo "⚠️ No se encontró .venv, intentando usar python del sistema..."
fi

# 3. Set PYTHONPATH
export PYTHONPATH="${ROOT_DIR}"
# export RAY_ADDRESS=auto  # Removed to allow local Ray init if no cluster exists

# 4. Check status of Ray (Optional/Auto-handled by src.main logic usually)
# pkill -f "ray" || true # Optional cleanup

# 5. Run Lucy Core
echo "🧠 Iniciando Lucy Core (src.main)..."
python -m src.main
