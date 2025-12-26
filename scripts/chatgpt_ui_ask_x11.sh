#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

# Require X11 access (avoid sandbox).
if [ -x "$DIR/x11_require_access.sh" ]; then
  "$DIR/x11_require_access.sh"
fi

# Auto-detect/ensure ChatGPT window id if not provided (VENTANA PUENTE)
if [ -z "${CHATGPT_WID_HEX:-}" ]; then
  if [ -x "$DIR/chatgpt_bridge_ensure.sh" ]; then
    CHATGPT_WID_HEX="$("$DIR/chatgpt_bridge_ensure.sh")"
  elif [ -x "$DIR/chatgpt_get_wid.sh" ]; then
    CHATGPT_WID_HEX="$("$DIR/chatgpt_get_wid.sh" || true)"
  fi
  export CHATGPT_WID_HEX
fi

QUESTION="${1:-}"
if [ -z "${QUESTION}" ]; then
  echo "USO: CHATGPT_WID_HEX=0x... $0 \"pregunta\"" >&2
  exit 2
fi

CHATGPT_WID_HEX="${CHATGPT_WID_HEX:-}"
if [ -z "${CHATGPT_WID_HEX}" ]; then
  echo "ERROR: seteá CHATGPT_WID_HEX (ej: 0x01e00017)" >&2
  exit 2
fi

TOKEN="$(date +%s)_$RANDOM"
ACTIVE_WID="$(xdotool getactivewindow 2>/dev/null || true)"

PROMPT="LUCY_REQ_${TOKEN}: ${QUESTION}

Respondé SOLO con UNA línea.
Debe empezar EXACTAMENTE con: LUCY_ANSWER_${TOKEN}: (dos puntos y un espacio)
y en ESA MISMA LÍNEA, después de eso, poné tu respuesta."

# Pegar prompt
CHATGPT_WID_HEX="$CHATGPT_WID_HEX" ./scripts/chatgpt_focus_paste.sh "$PROMPT" >/dev/null

# Enviar
CHATGPT_WID_DEC=$((CHATGPT_WID_HEX))
xdotool key --window "$CHATGPT_WID_DEC" Return

# Volver el foco a la ventana original (para que Ctrl-C funcione en la terminal)
if [ -n "${ACTIVE_WID:-}" ]; then
  xdotool windowactivate "$ACTIVE_WID" >/dev/null 2>&1 || true
fi

# Esperar respuesta
ASK_TIMEOUT="${ASK_TIMEOUT:-75}"
deadline=$((SECONDS+ASK_TIMEOUT))
while [ $SECONDS -lt $deadline ]; do
  ACTIVE_LOOP_WID="$(xdotool getactivewindow 2>/dev/null || true)"
  text="$(CHATGPT_WID_HEX="$CHATGPT_WID_HEX" ./scripts/chatgpt_copy_chat_text.sh 2>/dev/null || true)"
  if [ -n "${ACTIVE_LOOP_WID:-}" ]; then
    xdotool windowactivate "$ACTIVE_LOOP_WID" >/dev/null 2>&1 || true
  fi
  line="$(printf '%s\n' "$text" | grep -E "^LUCY_ANSWER_${TOKEN}:" | tail -n 1 || true)"
  if [ -n "$line" ]; then
    echo "$line"
    exit 0
  fi
  sleep 2
done

echo "ERROR: timeout esperando LUCY_ANSWER_${TOKEN}:" >&2
exit 1
