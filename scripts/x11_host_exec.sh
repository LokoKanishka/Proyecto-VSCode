#!/usr/bin/env bash
set -euo pipefail

# Ejecuta un comando X11 desde "host" si esta shell está sandboxeada (Seccomp/NoNewPrivs).
# Prioridad de escape:
#   1) Flatpak: flatpak-spawn --host
#   2) systemd-run --user (si hay acceso al user bus)
# Si nada sirve, falla con un mensaje claro.

need_escape() {
  python3 - <<'PY' >/dev/null 2>&1
import socket, errno
s=socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
try:
    s.connect("/tmp/.X11-unix/X0")
    raise SystemExit(0)            # OK: no sandbox bloqueando
except OSError as e:
    raise SystemExit(1 if e.errno == errno.EPERM else 2)  # 1=EPERM sandbox
finally:
    try: s.close()
    except: pass
PY
  rc=$?
  [[ $rc -eq 1 ]]
}

is_flatpak() {
  [[ -f "/.flatpak-info" ]] || env | grep -q '^FLATPAK_ID='
}

can_systemd_run() {
  command -v systemd-run >/dev/null 2>&1 || return 1
  systemd-run --user --quiet /usr/bin/true >/dev/null 2>&1
}

if [[ $# -lt 1 ]]; then
  echo "usage: $0 <cmd> [args...]" >&2
  exit 2
fi

printf -v QCMD '%q ' "$@"

DISP="${DISPLAY:-:0}"
XAUTH="${XAUTHORITY:-/run/user/$(id -u)/gdm/Xauthority}"
if [[ ! -r "$XAUTH" && -r "$HOME/.Xauthority" ]]; then
  XAUTH="$HOME/.Xauthority"
fi

if need_escape; then
  # 1) Flatpak escape
  if is_flatpak && command -v flatpak-spawn >/dev/null 2>&1; then
    exec flatpak-spawn --host /usr/bin/env DISPLAY="$DISP" XAUTHORITY="$XAUTH" \
      /bin/bash -lc "cd '$PWD'; $QCMD"
  fi

  # 2) systemd-run escape
  if can_systemd_run; then
    exec systemd-run --user --pipe --wait --collect \
      /usr/bin/env DISPLAY="$DISP" XAUTHORITY="$XAUTH" \
      /bin/bash -lc "cd '$PWD'; $QCMD"
  fi

  echo "x11_host_exec: sandbox detectado (EPERM a /tmp/.X11-unix/X0) y no puedo escapar (sin flatpak-spawn ni systemd-run usable)." >&2
  echo "Ejecutá estos scripts desde una terminal host (GNOME Terminal), o instalá VS Code no-sandbox para dev." >&2
  exit 1
else
  exec /usr/bin/env DISPLAY="$DISP" XAUTHORITY="$XAUTH" \
    /bin/bash -lc "cd '$PWD'; $QCMD"
fi
