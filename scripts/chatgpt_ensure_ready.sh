#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
COPY_STRICT="$ROOT/scripts/chatgpt_copy_messages_strict.sh"

WID_HEX="${1:-${CHATGPT_WID_HEX:-}}"
if [[ -z "${WID_HEX:-}" ]]; then
  WID_HEX="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR_NO_WID" >&2
  exit 3
fi

WID_DEC="$(printf "%d" "$WID_HEX" 2>/dev/null || echo 0)"
if [[ "${WID_DEC}" -le 0 ]]; then
  echo "ERROR_INVALID_WID" >&2
  exit 3
fi

# Intentos suaves: cerrar burbuja "Restaurar páginas", overlays, y si aparece gate de ChatGPT,
# tabular hasta "Permanecer con la sesión cerrada" y enter.
MAX_TRIES="${CHATGPT_READY_TRIES:-4}"

ALLOW_GUEST="${CHATGPT_ALLOW_GUEST:-0}"

for n in $(seq 1 "$MAX_TRIES"); do
  set +e
  "$COPY_STRICT" >/dev/null 2>/tmp/lucy_copy_ready.err
  rc="$?"
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "__LUCY_READY__ OK try=$n wid=$WID_HEX" >&2
    exit 0
  fi

  if [[ "$rc" -ne 7 ]]; then
    echo "__LUCY_READY__ WARN try=$n rc=$rc (no es login), continuo..." >&2
  else
    echo "__LUCY_READY__ HIT login/bloqueo try=$n: intentando limpiar overlays..." >&2
  fi

  # Activar ventana + limpiar overlays
  geo="$("$HOST_EXEC" "xdotool getwindowgeometry --shell ${WID_DEC}" 2>/dev/null || true)"
  eval "$geo" || true
  : "${WIDTH:=1200}"
  : "${HEIGHT:=900}"
  cx=$(( WIDTH * 50 / 100 ))
  cy=$(( HEIGHT * 55 / 100 ))

  cmd="WID_HEX='$WID_HEX' WID_DEC='$WID_DEC' CX='$cx' CY='$cy'; "
  cmd+="set -euo pipefail; "
  cmd+="wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true; "
  cmd+="xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true; "
  cmd+="sleep 0.15; "
  cmd+="xdotool key --clearmodifiers Escape Escape 2>/dev/null || true; " # cierra bubble/overlays si responden a ESC
  cmd+="sleep 0.15; "
  cmd+="xdotool mousemove --window \"\$WID_DEC\" \"\$CX\" \"\$CY\" click 1 2>/dev/null || true; "
  cmd+="sleep 0.10; "
  cmd+="xdotool key --clearmodifiers Escape 2>/dev/null || true; "
  cmd+="sleep 0.10; "
  # Si estamos en gate de ChatGPT, normalmente el foco arranca en "Iniciar sesión".
  # Tab x2-3 + Enter suele caer en "Permanecer con la sesión cerrada" (si existe).
  cmd+="for i in 1 2 3; do xdotool key --clearmodifiers Tab 2>/dev/null || true; sleep 0.05; done; "
  cmd+="xdotool key --clearmodifiers Return 2>/dev/null || true; "
  cmd+="sleep 0.25; "
  "$HOST_EXEC" "$cmd" >/dev/null 2>&1 || true
done

# Último check para devolver rc=7 con mensaje claro (sin loops)
set +e
"$COPY_STRICT" >/dev/null 2>/tmp/lucy_copy_ready.err
rc="$?"
set -e
if [[ "$rc" -eq 7 ]]; then
  echo "ERROR_BLOCKED_LOGIN: seguís en login/bloqueo. Tenés que entrar a un chat válido (sesión/cookies) y reintentar." >&2
  exit 7
fi

echo "ERROR: ensure_ready no logró estabilizar UI (rc=$rc)" >&2
exit "$rc"
