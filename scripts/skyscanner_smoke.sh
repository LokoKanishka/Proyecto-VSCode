#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG="${ROOT_DIR}/logs/skyscanner_smoke.log"
mkdir -p "$(dirname "$LOG")"

if ! command -v firefox >/dev/null 2>&1; then
    echo "⚠️  Firefox no está instalado. Instalá firefox o ajustá LUCY_BROWSER_BIN." | tee "$LOG"
    exit 1
fi

echo "Iniciando smoke test Skyscanner..." | tee -a "$LOG"
cd "$ROOT_DIR"

./scripts/launch_skyscanner.sh &
PID=$!

trap 'echo "Deteniendo smoke..."; kill "$PID" >/dev/null 2>&1 || true; pkill firefox >/dev/null 2>&1 || true' EXIT

sleep 10

if command -v wmctrl >/dev/null 2>&1; then
    wmctrl -l | grep -i skyscanner | tee -a "$LOG"
else
    echo "wmctrl no disponible; no se puede verificar la ventana." | tee -a "$LOG"
fi

echo "Smoke test completado; cerrando firefox." | tee -a "$LOG"
pkill firefox >/dev/null 2>&1 || true
kill "$PID" >/dev/null 2>&1 || true
trap - EXIT
