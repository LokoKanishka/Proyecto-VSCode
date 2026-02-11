#!/bin/bash
# LUCY - Parallel Swarm Initiator
# Optimizado para arranque paralelo con health-checks
# t_arranque = max(t_i) + ε (en lugar de Σt_i)

set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${ROOT_DIR}"

MODE="${LUCY_MODE:-swarm}"
PY_BIN="${PY_BIN:-python3}"

# Header minimalista
echo "⚡ LUCY Swarm Initiator"

# Pre-flight check paralelo
if [ -f "scripts/preflight_check.py" ]; then
    if ! "${PY_BIN}" scripts/preflight_check.py; then
        echo ""
        echo "🔍 Revisa los archivos críticos listados arriba"
        exit 1
    fi
else
    # Fallback: verificación básica si preflight_check no existe
    echo "🔍 Pre-flight checks... ⏭️ (usando fallback)"
    if [ ! -f "src/engine/swarm_runner.py" ]; then
        echo "❌ src/engine/swarm_runner.py no encontrado"
        exit 1
    fi
fi

# Configurar swarm console si es necesario
if [ "${MODE}" = "swarm" ] && [ -z "${LUCY_SWARM_CONSOLE}" ]; then
    export LUCY_SWARM_CONSOLE=1
fi

# Lanzamiento del swarm (ahora con paralelismo interno)
# El swarm_runner.py se encarga del lanzamiento paralelo de componentes
exec "${PY_BIN}" scripts/run_lucy.py --mode "${MODE}"
