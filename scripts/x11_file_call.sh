#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

IPC_DIR="${X11_FILE_IPC_DIR:-$REPO_ROOT/diagnostics/x11_file_ipc}"
INBOX="$IPC_DIR/inbox"
OUTBOX="$IPC_DIR/outbox"
mkdir -p "$INBOX" "$OUTBOX"

# comando: si te pasan un solo argumento, lo tomamos como string crudo.
# si te pasan varios, los quotearmos como argv.
if [[ $# -lt 1 ]]; then
  echo "USO: $0 <cmd...>   |   $0 'cmd con pipes'" >&2
  exit 2
fi

if [[ $# -eq 1 ]]; then
  CMD="$1"
else
  printf -v CMD '%q ' "$@"
fi

TOKEN="$(date +%s)_$RANDOM"
REQ_TMP="$INBOX/.req_${TOKEN}.tmp"
REQ="$INBOX/req_${TOKEN}.txt"
RES="$OUTBOX/res_${TOKEN}.txt"

printf '%s\n' "$CMD" > "$REQ_TMP"
mv -f "$REQ_TMP" "$REQ"

# esperar respuesta
TIMEOUT="${X11_FILE_CALL_TIMEOUT:-120}"
deadline=$((SECONDS+TIMEOUT))
while [[ $SECONDS -lt $deadline ]]; do
  if [[ -f "$RES" ]]; then
    cat "$RES"
    rm -f "$RES" >/dev/null 2>&1 || true
    exit 0
  fi
  sleep 0.15
done

echo "RC=124" >&2
echo "ERROR: timeout esperando $RES" >&2
exit 124
