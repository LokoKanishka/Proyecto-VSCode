#!/usr/bin/env bash
set -euo pipefail

if command -v xvfb-run >/dev/null 2>&1; then
  xvfb-run --auto-servernum --server-args="-screen 0 1366x768x24" ./scripts/skyscanner_smoke.sh
else
  echo "xvfb-run no disponible. Instalá xvfb o ejecutá scripts/skyscanner_smoke.sh en un entorno gráfico."
  exit 1
fi
