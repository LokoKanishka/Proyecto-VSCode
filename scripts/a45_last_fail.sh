#!/usr/bin/env bash
set -euo pipefail

LATEST_LOGDIR="$(ls -td /tmp/lucy_a45_runner_* 2>/dev/null | head -n1 || true)"

if [[ -z "$LATEST_LOGDIR" ]]; then
  echo "No hay registros de ejecutores A45 en /tmp."
  exit 1
fi

echo "Resumen del último runner: $LATEST_LOGDIR"
echo "=== fail.txt ==="
cat "$LATEST_LOGDIR/fail.txt" 2>/dev/null || echo "(fail.txt no existe)"
echo
echo "=== runner.log (últimas 200 líneas) ==="
tail -n 200 "$LATEST_LOGDIR/runner.log" 2>/dev/null || true
echo
echo "=== Contenido del directorio ==="
ls -la "$LATEST_LOGDIR"
echo
if [[ -f "$LATEST_LOGDIR/last_verify.log" ]]; then
  echo "=== last_verify.log (tail) ==="
  tail -n 200 "$LATEST_LOGDIR/last_verify.log" || true
  echo
fi
if [[ -f "$LATEST_LOGDIR/stress.summary.tsv" ]]; then
  echo "=== stress.summary.tsv ==="
  cat "$LATEST_LOGDIR/stress.summary.tsv"
  echo
fi
