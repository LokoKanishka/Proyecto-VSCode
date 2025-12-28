#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

SOCK_DEFAULT="${REPO_ROOT}/diagnostics/x11_agent.sock"
SOCK="${X11_AGENT_SOCK:-$SOCK_DEFAULT}"
export X11_AGENT_SOCK="$SOCK"

# 1 arg => comando crudo (puede incluir pipes). Varios args => quote seguro.
if [ $# -eq 1 ]; then
  CMD="$1"
else
  CMD="$(printf '%q ' "$@")"
fi
export CMD

python3 - <<'PY'
import os, socket, sys, re

cmd = os.environ["CMD"].rstrip()
tcp = os.environ.get("X11_AGENT_TCP", "").strip()
sock_path = os.path.expanduser(os.environ.get("X11_AGENT_SOCK", ""))

def read_all(s):
    buf = b""
    while True:
        chunk = s.recv(4096)
        if not chunk:
            break
        buf += chunk
    return buf

def parse_and_exit(payload: bytes):
    text = payload.decode("utf-8", "replace")
    first, _, rest = text.partition("\n")
    m = re.match(r"^RC=(\d+)$", first.strip())
    if m:
        rc = int(m.group(1))
        out = rest
    else:
        rc = 0
        out = text
    sys.stdout.write(out)
    sys.exit(rc)

# Prefer TCP (AF_INET) si está seteado: X11_AGENT_TCP=127.0.0.1:47391
if tcp and ":" in tcp:
    host, port_s = tcp.rsplit(":", 1)
    host = host.strip() or "127.0.0.1"
    port = int(port_s.strip())
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host, port))
    s.sendall((cmd + "\n").encode("utf-8"))
    payload = read_all(s)
    s.close()
    parse_and_exit(payload)

# Fallback: UNIX socket
if not sock_path:
    print("x11_agent_call: no hay X11_AGENT_TCP ni X11_AGENT_SOCK", file=sys.stderr)
    sys.exit(2)

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect(sock_path)
s.sendall((cmd + "\n").encode("utf-8"))
payload = read_all(s)
s.close()
parse_and_exit(payload)
PY
