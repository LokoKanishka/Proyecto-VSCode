#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT_DIR}"

MODE="${LUCY_MODE:-gui}"
PY_BIN="${PY_BIN:-python3}"

echo "🚀 Verificando sintaxis..."
if "${PY_BIN}" -m py_compile src/engine/voice_bridge.py; then
    echo "✅ Código válido. Ejecutando modo: ${MODE}"
    "${PY_BIN}" scripts/run_lucy.py --mode "${MODE}"
else
    echo "❌ ERROR FATAL DE SINTAXIS. Revisa el copiado/pegado."
    read -p "Presiona Enter para salir..."
fi
