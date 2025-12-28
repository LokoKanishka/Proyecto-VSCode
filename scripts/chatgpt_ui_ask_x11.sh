#!/usr/bin/env bash
set -euo pipefail


POLL_SLEEP="${LUCY_ASK_POLL_SLEEP:-2}"
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

REQ_ACCESS="$ROOT/scripts/x11_require_access.sh"
ENSURE="$ROOT/scripts/chatgpt_bridge_ensure.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
SEND="$ROOT/scripts/chatgpt_ui_send_x11.sh"
COPY="$ROOT/scripts/chatgpt_copy_chat_text.sh"

PROMPT="${1:-}"
if [[ -z "${PROMPT:-}" ]]; then
  echo "ERROR: usage: $0 <prompt>" >&2
  exit 2
fi

# Preflight (en sandbox, require_access ya bypassa si hay IPC)
if ! "$REQ_ACCESS" >/dev/null 2>&1; then
  echo "ERROR: no hay acceso X11 (ni IPC disponible)." >&2
  exit 111
fi

# Ensure bridge + WID
"$ENSURE" >/dev/null 2>&1 || true
WID="${CHATGPT_WID_HEX:-$("$GET_WID" 2>/dev/null || true)}"
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX" >&2
  exit 3
fi
export CHATGPT_WID_HEX="$WID"

TS="$(date +%s)"
RID="$(( (RANDOM % 90000) + 10000 ))"
TOKEN="${TS}_${RID}"

REQ="LUCY_REQ_${TOKEN}: ${PROMPT}"
INSTR=$'Respondé SOLO con UNA línea.\nDebe empezar EXACTAMENTE con: LUCY_ANSWER_'"${TOKEN}"$': (dos puntos y un espacio)\ny en ESA MISMA LÍNEA, después de eso, poné tu respuesta.'
MSG="${REQ}"$'\n\n'"${INSTR}"

# Sanitiza control chars (incluye DEL 0x7f y CR)
sanitize() {
  tr -d '\r' | LC_ALL=C tr -d '\000-\010\013\014\016-\037\177'
}

copy_chat_to() {
  local out="$1"
  # OJO: copy puede mover mouse; mantenemos llamadas mínimas
  timeout 25s "$COPY" >"$out" 2>/dev/null || true
}

chat_has() {
  local file="$1" needle="$2"
  sanitize <"$file" | grep -Fq "$needle"
}

extract_answer_line() {
  local file="$1"
  # OJO: matchea SOLO si la línea empieza con LUCY_ANSWER_<token>:
  sanitize <"$file" | grep -E "^LUCY_ANSWER_${TOKEN}:" | tail -n 1 || true
}

TMP="$(mktemp /tmp/lucy_ask_${TOKEN}.XXXX.txt)"
trap 'rm -f "$TMP" 2>/dev/null || true' EXIT

# 1) SEND con verificación: si no aparece el LUCY_REQ_<token>, reintenta foco+send
SENT_OK=0
for attempt in 1 2 3; do
  # enviar
  "$SEND" "$MSG" >/dev/null 2>/dev/null || true
  sleep 0.9

  # confirmar que el REQ aparece en el chat copiado
  copy_chat_to "$TMP"
  if chat_has "$TMP" "LUCY_REQ_${TOKEN}:"; then
    SENT_OK=1
    break
  fi
done

if [[ "$SENT_OK" -ne 1 ]]; then
  echo "ERROR: el ASK no llegó a publicarse en el chat (no vi LUCY_REQ_${TOKEN}:). Ejecutá /tmp/lucy_panic.sh si te agarró el mouse." >&2
  exit 4
fi

# 2) Esperar respuesta (polls pocos; normalmente responde rápido)
TIMEOUT_SEC="${CHATGPT_ASK_TIMEOUT_SEC:-90}"
POLL_SEC=2
MAX_POLLS=$(( TIMEOUT_SEC / POLL_SEC ))
if [[ "$MAX_POLLS" -lt 5 ]]; then MAX_POLLS=5; fi

for _ in $(seq 1 "$MAX_POLLS"); do
  copy_chat_to "$TMP"
  line="$(extract_answer_line "$TMP")"
  if [[ -n "${line:-}" ]]; then
    printf '%s\n' "$line"
    exit 0
  fi
  sleep "$POLL_SEC"
done

echo "ERROR: timeout esperando LUCY_ANSWER_${TOKEN}:" >&2
exit 1
