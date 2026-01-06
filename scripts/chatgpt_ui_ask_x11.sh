#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# --- AUTO IPC DIR (A3.12) ---
if [[ -z "${X11_FILE_IPC_DIR:-}" ]]; then
  export X11_FILE_IPC_DIR="$ROOT/diagnostics/x11_file_ipc"
fi
# ----------------------------

REQ_ACCESS="$ROOT/scripts/x11_require_access.sh"
ENSURE="$ROOT/scripts/chatgpt_bridge_ensure.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
SEND="$ROOT/scripts/chatgpt_ui_send_x11.sh"
COPY="$ROOT/scripts/chatgpt_copy_chat_text.sh"
DISP="$ROOT/scripts/x11_dispatcher.py"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

PROMPT="${1:-}"
if [[ -z "${PROMPT:-}" ]]; then
  echo "ERROR: usage: $0 <prompt>" >&2
  exit 2
fi

# Preflight
if ! "$REQ_ACCESS" >/dev/null 2>&1; then
  echo "ERROR: no hay acceso X11 (ni IPC disponible)." >&2
  exit 111
fi

# Ensure bridge (no fatal)
"$ENSURE" >/dev/null 2>&1 || true

resolve_wid() {
  # 1) env
  if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
    printf '%s\n' "$CHATGPT_WID_HEX"
    return 0
  fi

  # 2) selector estable (ya usa host_exec en este entorno)
  local w=""
  w="$("$GET_WID" 2>/dev/null || true)"
  if [[ -n "${w:-}" ]]; then
    printf '%s\n' "$w"
    return 0
  fi

  # 3) hard fallback: host_exec + filtro por título
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" 'wmctrl -lx' 2>/dev/null \
    | awk '
      BEGIN{best=""; bestScore=-1}
      {
        wid=$1; cls=$3;
        title="";
        for(i=4;i<=NF;i++){ title=title (i==4?"":" ") $i }
        if(cls!="google-chrome.Google-chrome") next;
        if(index(title,"ChatGPT")==0) next;
        if(index(title,"V.S.Code")>0) next;
        score=10;
        if(index(title,"ChatGPT - Google Chrome")>0) score=90;
        if(score>bestScore){bestScore=score; best=wid}
      }
      END{print best}
    ' | head -n 1
    return 0
  fi

  return 0
}

WID="$(resolve_wid || true)"
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

sanitize() {
  tr -d '\r' | LC_ALL=C tr -d '\000-\010\013\014\016-\037\177'
}

copy_chat_to() {
  local out="$1"
  timeout 25s "$COPY" >"$out" 2>/dev/null || true
}

chat_has() {
  local file="$1" needle="$2"
  sanitize <"$file" | grep -Fq "$needle"
}

extract_answer_line() {
  local file="$1"
  sanitize <"$file" | grep -E "^LUCY_ANSWER_${TOKEN}:" | tail -n 1 || true
}

TMP="$(mktemp /tmp/lucy_ask_${TOKEN}.XXXX.txt)"
trap 'rm -f "$TMP" 2>/dev/null || true' EXIT

# 1) SEND + verificar que el REQ aparece
SENT_OK=0
for attempt in 1 2 3; do
  "$SEND" "$MSG" >/dev/null 2>/dev/null || true
  sleep 0.9
  copy_chat_to "$TMP"
  if chat_has "$TMP" "LUCY_REQ_${TOKEN}:"; then
    SENT_OK=1
    break
  fi
done

if [[ "$SENT_OK" -ne 1 ]]; then
  echo "ERROR: el ASK no llegó a publicarse en el chat (no vi LUCY_REQ_${TOKEN}:)." >&2
  exit 4
fi

# 2) Esperar respuesta
TIMEOUT_SEC="${CHATGPT_ASK_TIMEOUT_SEC:-90}"
POLL_SEC=2
MAX_POLLS=$(( TIMEOUT_SEC / POLL_SEC ))
if [[ "$MAX_POLLS" -lt 5 ]]; then MAX_POLLS=5; fi

# --- A3_12_WATCHDOG ---
# Si no aparece respuesta tras N polls, hacemos “nudge” (foco + End + click panel).
# Si sigue sin aparecer, hacemos refresh (Ctrl+R) una vez.
NUDGE_AT="${CHATGPT_ASK_NUDGE_AT:-18}"      # ~36s si POLL_SEC=2
RELOAD_AT="${CHATGPT_ASK_RELOAD_AT:-35}"    # ~70s si POLL_SEC=2
DID_RELOAD=0

# --- A3_12_RESEND_AFTER_RELOAD ---
# Si el backend web queda colgado (intermitente), tras reload re-enviamos el mismo MSG y seguimos esperando.
RESEND_AFTER_RELOAD="${CHATGPT_ASK_RESEND_AFTER_RELOAD:-1}"
# --- /A3_12_RESEND_AFTER_RELOAD ---

nudge_ui() {
  # Best-effort: no debe matar el ask si falla
  python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true
  python3 -u "$DISP" send_keys "$WID" "End" >/dev/null 2>/dev/null || true
  # click al centro del panel (suele devolver foco a la conversación)
  python3 -u "$DISP" click "$WID" "0.55" "0.50" >/dev/null 2>/dev/null || true
}

reload_ui() {
  # Ctrl+R (si la pestaña quedó colgada, esto suele destrabar)
  python3 -u "$DISP" focus_window "$WID" >/dev/null 2>/dev/null || true
  python3 -u "$DISP" send_keys "$WID" "ctrl+r" >/dev/null 2>/dev/null || true
  sleep 6
}
# --- /A3_12_WATCHDOG ---

i=0
for _ in $(seq 1 "$MAX_POLLS"); do
  i=$((i+1))
  copy_chat_to "$TMP"
  line="$(extract_answer_line "$TMP")"
  if [[ -n "${line:-}" ]]; then
    printf '%s\n' "$line"
    exit 0
  fi
  if [[ "$i" -eq "$NUDGE_AT" ]]; then
    nudge_ui
  fi
  if [[ "$i" -eq "$RELOAD_AT" ]] && [[ "$DID_RELOAD" -ne 1 ]]; then
    DID_RELOAD=1
    reload_ui

    # Re-enviar el mismo mensaje (mismo token) si está habilitado
    if [[ "${RESEND_AFTER_RELOAD:-1}" -eq 1 ]]; then
      "$SEND" "$MSG" >/dev/null 2>/dev/null || true
      sleep 0.9
    fi
  fi
  sleep "$POLL_SEC"
done

echo "ERROR: timeout esperando LUCY_ANSWER_${TOKEN}:" >&2
exit 1
