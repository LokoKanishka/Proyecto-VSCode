#!/usr/bin/env bash
set -euo pipefail

# Ensure X11 env (non-interactive safe)
export DISPLAY="${DISPLAY:-:0}"
if [ -z "${XAUTHORITY:-}" ]; then
  if [ -f "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
  elif [ -f "/run/user/$UID/gdm/Xauthority" ]; then
    export XAUTHORITY="/run/user/$UID/gdm/Xauthority"
  else
    cand="$(ls -1 /run/user/$UID/.mutter-Xwaylandauth.* 2>/dev/null | head -n 1 || true)"
    [ -n "$cand" ] && export XAUTHORITY="$cand"
  fi
fi


DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
QUESTION="${1:-}"
[ -n "$QUESTION" ] || { echo "USO: $0 \"pregunta\"" >&2; exit 2; }

WID_HEX="${CHATGPT_WID_HEX:-$("$DIR/chatgpt_get_wid.sh")}"
WID_DEC=$((WID_HEX))

TOKEN="$(date +%s)_${RANDOM}"
REQ_LABEL="LUCY_REQ_${TOKEN}"
ANS_LABEL="LUCY_ANSWER_${TOKEN}"

PROMPT="${REQ_LABEL}: ${QUESTION}

Respondé SOLO con UNA línea que empiece exactamente así:
${ANS_LABEL}: <tu respuesta en una sola línea>"

# 1) pegar prompt
CHATGPT_WID_HEX="$WID_HEX" "$DIR/chatgpt_focus_paste.sh" "$PROMPT" >/dev/null

# 2) enviar
xdotool key --window "$WID_DEC" Return

# 3) esperar respuesta real (no placeholder)
deadline=$((SECONDS+60))
while [ $SECONDS -lt $deadline ]; do
  txt="$(CHATGPT_WID_HEX="$WID_HEX" "$DIR/chatgpt_copy_chat_text.sh" 2>/dev/null || true)"
  ans="$(printf '%s\n' "$txt" | python3 "$DIR/chatgpt_extract_answer.py" "$ANS_LABEL" 2>/dev/null || true)"
  if [ -n "${ans:-}" ]; then
    echo "$ans"
    exit 0
  fi
  sleep 1
done

echo "ERROR: timeout esperando ${ANS_LABEL}:" >&2
exit 1
