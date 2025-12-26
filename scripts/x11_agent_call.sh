#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Resolver socket con fallback (evita ~/.cache si el sandbox lo bloquea)
if [[ -n "${X11_AGENT_SOCK:-}" ]]; then
  SOCK="$(python3 - <<'PY'
import os
from pathlib import Path
print(str(Path(os.environ["X11_AGENT_SOCK"]).expanduser()))
PY
)"
else
  CAND1="$HOME/.cache/lucy/x11_agent.sock"
  CAND2="$REPO_ROOT/diagnostics/x11_agent.sock"
  if [[ -S "$CAND1" ]]; then
    SOCK="$CAND1"
  else
    SOCK="$CAND2"
  fi
fi

[[ -S "$SOCK" ]] || { echo "x11_agent_call: socket no existe: $SOCK" >&2; exit 2; }

CMD="$(printf '%q ' "$@")"
SOCK="$SOCK" CMD="$CMD" python3 - <<'PY'
import os, socket, sys
sock_path = os.environ["SOCK"]
cmd = os.environ["CMD"].rstrip()

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(sock_path)
s.sendall((cmd + "\n").encode("utf-8"))

buf = b""
while True:
    chunk = s.recv(4096)
    if not chunk:
        break
    buf += chunk

sys.stdout.write(buf.decode("utf-8", "replace"))
PY
