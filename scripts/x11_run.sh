#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

CALL="${SCRIPT_DIR}/x11_file_call.sh"
IPC_DIR="${X11_FILE_IPC_DIR:-${REPO_ROOT}/diagnostics/x11_file_ipc}"

# arma comando: si te pasan muchos args, los quotea seguro
if [[ $# -lt 1 ]]; then
  echo "usage: $0 <cmd...>  |  $0 'cmd string con pipes'" >&2
  exit 2
fi

if [[ $# -eq 1 ]]; then
  CMD="$1"
else
  printf -v CMD '%q ' "$@"
fi

if [[ -x "$CALL" && -d "$IPC_DIR/inbox" && -d "$IPC_DIR/outbox" ]]; then
  export X11_FILE_IPC_DIR="$IPC_DIR"
  out="$("$CALL" "$CMD" || true)"
  rc_line="$(printf '%s\n' "$out" | head -n 1 || true)"
  if [[ "$rc_line" =~ ^RC=([0-9]+)$ ]]; then
    rc="${BASH_REMATCH[1]}"
    # cuerpo (sin RC=)
    printf '%s\n' "$out" | tail -n +2
    exit "$rc"
  else
    # por si el call no trae RC=...
    printf '%s\n' "$out"
    exit 0
  fi
fi

# fallback: si no hay agente, intenta local (puede fallar en sandbox)
exec /bin/bash -lc "$CMD"
