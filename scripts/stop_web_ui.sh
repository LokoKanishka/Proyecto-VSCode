#!/usr/bin/env bash
set -euo pipefail

echo "🛑 Deteniendo Lucy Voice Web UI..."
pid=$(pgrep -f "lucy_web/app.py" || true)
if [ -z "$pid" ]; then
    echo "No se encontró proceso activo."
    exit 0
fi

kill "$pid"
sleep 1
echo "Proceso $pid terminado."
