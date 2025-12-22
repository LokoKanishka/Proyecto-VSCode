#!/usr/bin/env bash
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "${ROOT}" ]]; then
  echo "ERROR: no estás adentro de un repo git. Entrá a ~/Lucy_Workspace/Proyecto-VSCode" >&2
  exit 1
fi
cd "$ROOT"

mkdir -p logs

SHA="$(git rev-parse --short HEAD 2>/dev/null || echo nogit)"
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
TS="$(date +%F_%H-%M-%S)"

LOG="logs/voice_${TS}_${BRANCH}_${SHA}.log"
META="logs/voice_${TS}_${BRANCH}_${SHA}.meta"
CMD="./scripts/lucy_voice_modular_node.sh"

if [[ ! -x "$CMD" ]]; then
  echo "ERROR: no encuentro ejecutable: $CMD" >&2
  echo "Contenido de ./scripts:" >&2
  ls -la ./scripts >&2 || true
  exit 1
fi

{
  echo "=== LUCY VOICE RUN META ==="
  echo "ts=$TS"
  echo "branch=$BRANCH"
  echo "sha=$SHA"
  echo "user=$(whoami)"
  echo "host=$(hostname)"
  echo "pwd=$(pwd)"
  echo "python=$(python3 --version 2>/dev/null || true)"
  echo "ollama=$(command -v ollama >/dev/null && ollama --version 2>/dev/null || echo missing)"
  echo "docker=$(command -v docker >/dev/null && docker --version 2>/dev/null || echo missing)"
  echo "env:LUCY_SEARXNG_SUMMARY=${LUCY_SEARXNG_SUMMARY-}"
  echo "env:LUCY_SEARXNG_URL=${LUCY_SEARXNG_URL-}"
  echo "==========================="
} > "$META"

cleanup() {
  stty sane 2>/dev/null || true
  stty echo 2>/dev/null || true
}
trap cleanup EXIT

echo "[runlog] PTY log:  $LOG"
echo "[runlog] META:     $META"
echo "[runlog] Ejecuta:  $CMD"
echo "[runlog] Salida por voz: \"lucy dormi\"  (o Ctrl+C)"

# preferimos -e si existe (util-linux nuevo). Si no, caemos a modo sin -e.
if script --help 2>&1 | grep -q -- " -e,"; then
  script -q -f -e -c "$CMD" "$LOG"
else
  script -q -f -c "$CMD" "$LOG"
fi

echo "[runlog] Fin. Últimas 40 líneas:"
tail -n 40 "$LOG" || true

echo "[runlog] Archivos generados:"
ls -lh "$LOG" "$META"
