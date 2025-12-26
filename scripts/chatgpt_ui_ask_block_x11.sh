#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIR="$SCRIPT_DIR"

if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

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
if [ -z "$QUESTION" ]; then
  echo "USO: CHATGPT_WID_HEX=0x... $0 \"pregunta\"" >&2
  exit 2
fi

[ -n "${CHATGPT_WID_HEX:-}" ] || { echo "ERROR: no hay CHATGPT_WID_HEX"; exit 2; }

TOKEN="$(date +%s)_$RANDOM"
ACTIVE_WID="$(xdotool getactivewindow 2>/dev/null || true)"

START="LUCY_BLOCK_${TOKEN}:"
END="LUCY_END_${TOKEN}"

PROMPT="LUCY_REQ_${TOKEN}: ${QUESTION}

Respondé SOLO con este bloque multilínea, sin texto fuera del bloque.
Entre las dos marcas poné el contenido:

${START}
${END}"

CHATGPT_WID_HEX="$CHATGPT_WID_HEX" "${REPO_ROOT}/scripts/chatgpt_focus_paste.sh" "$PROMPT" >/dev/null
xdotool key --window "$((CHATGPT_WID_HEX))" Return

if [ -n "${ACTIVE_WID:-}" ]; then
  xdotool windowactivate "$ACTIVE_WID" >/dev/null 2>&1 || true
fi

ASK_TIMEOUT="${ASK_TIMEOUT:-120}"
deadline=$((SECONDS+ASK_TIMEOUT))

while [ $SECONDS -lt $deadline ]; do
  ACTIVE_LOOP_WID="$(xdotool getactivewindow 2>/dev/null || true)"
  text="$(CHATGPT_WID_HEX="$CHATGPT_WID_HEX" "${REPO_ROOT}/scripts/chatgpt_copy_chat_text.sh" 2>/dev/null || true)"
  if [ -n "${ACTIVE_LOOP_WID:-}" ]; then
    xdotool windowactivate "$ACTIVE_LOOP_WID" >/dev/null 2>&1 || true
  fi

  if printf '%s\n' "$text" | grep -qE "^${START}$" && printf '%s\n' "$text" | grep -qE "^${END}$"; then
    out="$(printf '%s
' "$text" | awk -v s="$START" -v e="$END" '
      $0==s {inside=1; buf=""; next}
      inside && $0==e {last=buf; inside=0; next}
      inside {buf = buf $0 ORS}
      END {printf "%s", last}
    ')"
    if [ -n "${out:-}" ]; then
      printf '%s\n' "$out"
      exit 0
    fi
  fi

  sleep 2
done

echo "ERROR: timeout esperando bloque ${START} ... ${END}" >&2
exit 1
