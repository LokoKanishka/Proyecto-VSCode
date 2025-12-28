#!/usr/bin/env bash
set -euo pipefail

# If file-agent IPC is available, allow without direct X11 socket access.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CALL="$REPO_ROOT/scripts/x11_file_call.sh"
IPC_DIR="${X11_FILE_IPC_DIR:-$REPO_ROOT/diagnostics/x11_file_ipc}"
if [[ -x "$CALL" && -d "$IPC_DIR/inbox" && -d "$IPC_DIR/outbox" ]]; then
  exit 0
fi

# Requires real access to the X11 socket; sandboxed shells often get EPERM.
disp="${DISPLAY:-}"
if [[ -z "$disp" ]]; then
  echo "ERROR: DISPLAY is not set (no visible X11 session)." >&2
  exit 111
fi

# Supports :0 or :0.0 formats.
d="${disp#*:}"
d="${d%%.*}"
sock="/tmp/.X11-unix/X${d}"

python3 - <<PY
import socket
import sys

sock_path = "${sock}"
s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    s.connect(sock_path)
except PermissionError:
    print("ERROR: no permission to connect to X11 (" + sock_path + ").", file=sys.stderr)
    print("Probable cause: running inside a sandbox (GNOME Code / VS Code Snap/Flatpak).", file=sys.stderr)
    print("Fix: run these scripts from GNOME Terminal (host).", file=sys.stderr)
    sys.exit(111)
except FileNotFoundError:
    print("ERROR: X11 socket not found: " + sock_path, file=sys.stderr)
    sys.exit(111)
except OSError as e:
    print("ERROR: cannot connect to X11: %r" % (e,), file=sys.stderr)
    sys.exit(111)
finally:
    s.close()
PY
