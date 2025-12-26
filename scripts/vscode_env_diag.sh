#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p diagnostics

echo "== DATE =="
date
echo

echo "== WHOAMI / PIDS =="
echo "USER=$USER"
echo "PID=$$"
echo "PPID=$PPID"
ps -o pid=,ppid=,comm=,args= -p $$ -p "$PPID" || true
echo

echo "== CGROUP =="
cat /proc/$$/cgroup || true
echo

echo "== ENV HINTS =="
env | grep -E 'VSCODE|TERM_PROGRAM|FLATPAK|SNAP|DISPLAY|XAUTHORITY|XDG_SESSION_TYPE|WAYLAND_DISPLAY' | sort || true
echo

echo "== X11 SOCKET TEST (/tmp/.X11-unix/X0) =="
python3 - <<'PY' || true
import os
import socket
import stat

p = "/tmp/.X11-unix/X0"
print("path:", p)
try:
    st = os.stat(p)
    print("mode:", oct(stat.S_IMODE(st.st_mode)), "uid:", st.st_uid, "gid:", st.st_gid)
except Exception as e:
    print("stat: FAIL", repr(e))
try:
    s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    s.settimeout(1.5)
    s.connect(p)
    print("connect: OK")
except Exception as e:
    print("connect: FAIL", repr(e), "errno=", getattr(e, "errno", None))
PY
echo

echo "== x11_env + wmctrl (si existe scripts/x11_env.sh) =="
if [ -r "scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "scripts/x11_env.sh"
  echo "[x11_env] DISPLAY=${DISPLAY-<unset>}"
  echo "[x11_env] XAUTHORITY=${XAUTHORITY-<unset>}"
fi
set +e
out="$(wmctrl -lx 2>&1)"
rc=$?
set -e
echo "wmctrl_rc=$rc"
echo "$out" | head -n 60
echo

echo "== GUARD (scripts/x11_require_access.sh) =="
if [ -x "scripts/x11_require_access.sh" ]; then
  set +e
  ./scripts/x11_require_access.sh
  echo "RC_guard=$?"
  set -e
else
  echo "NO scripts/x11_require_access.sh"
fi
