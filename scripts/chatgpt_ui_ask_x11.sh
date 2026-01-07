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

  return 0
}

get_wid_title() {
  local wid="$1"
  if [[ -x "$HOST_EXEC" ]]; then
    "$HOST_EXEC" "wmctrl -l | awk '\$1==\"${wid}\" { \$1=\"\"; \$2=\"\"; \$3=\"\"; sub(/^ +/, \"\"); print; exit }'" 2>/dev/null || true
  fi
}

WID="$(resolve_wid || true)"
if [[ -z "${WID:-}" ]]; then
  "$ENSURE" >/dev/null 2>&1 || true
  WID="$(resolve_wid || true)"
fi
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no pude resolver CHATGPT_WID_HEX" >&2
  exit 3
fi

TITLE="$(get_wid_title "$WID")"
if [[ "${TITLE}" == *"V.S.Code"* ]]; then
  "$ENSURE" >/dev/null 2>&1 || true
  WID="$(resolve_wid || true)"
  TITLE="$(get_wid_title "$WID")"
  if [[ "${TITLE}" == *"V.S.Code"* ]]; then
    echo "ERROR: BAD_WID_VSCODE WID=${WID} TITLE=${TITLE}" >&2
    exit 3
  fi
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
POLL_SEC="${POLL_SEC:-2}"
STALL_POLLS="${STALL_POLLS:-12}"
MAX_POLLS=$(( TIMEOUT_SEC / POLL_SEC ))
if [[ "$MAX_POLLS" -lt 5 ]]; then MAX_POLLS=5; fi

# --- A3_12_WATCHDOG ---
# Si no aparece respuesta tras N polls, hacemos “nudge” (foco + End + click panel).
# Si sigue sin aparecer, hacemos refresh (Ctrl+R) una vez.
NUDGE_AT="${CHATGPT_ASK_NUDGE_AT:-18}"      # ~36s si POLL_SEC=2
RELOAD_AT="${CHATGPT_ASK_RELOAD_AT:-35}"    # ~70s si POLL_SEC=2
DID_NUDGE=0
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
stall_count=0
prev_copy_bytes=0
prev_copy_sha=""
prev_shot_sha=""

hash_file() {
  local f="$1"
  if command -v sha1sum >/dev/null 2>&1; then
    sha1sum "$f" | awk '{print $1}'
    return 0
  fi
  cksum "$f" | awk '{print $1}'
}

for _ in $(seq 1 "$MAX_POLLS"); do
  i=$((i+1))
  copy_chat_to "$TMP"
  copy_bytes="$(wc -c < "$TMP" 2>/dev/null || echo 0)"
  copy_sha="NA"
  if [[ -f "$TMP" ]]; then
    copy_sha="$(hash_file "$TMP" 2>/dev/null || echo NA)"
  fi
  shot_sha="NA"
  progress=0
  if [[ -z "${prev_copy_sha}" ]]; then
    progress=1
  elif [[ "${copy_sha}" != "${prev_copy_sha}" ]]; then
    progress=1
  elif [[ $(( copy_bytes - prev_copy_bytes )) -ge 20 ]]; then
    progress=1
  elif [[ "${shot_sha}" != "NA" ]] && [[ -n "${prev_shot_sha}" ]] && [[ "${shot_sha}" != "${prev_shot_sha}" ]]; then
    progress=1
  fi

  if [[ "${progress}" -eq 1 ]]; then
    stall_count=0
  else
    stall_count=$((stall_count + 1))
  fi

  printf 'POLL i=%s copy_bytes=%s copy_sha=%s shot_sha=%s progress=%s stall=%s\n' \
    "$i" "$copy_bytes" "$copy_sha" "$shot_sha" "$progress" "$stall_count" >&2

  if [[ "${stall_count}" -eq "${STALL_POLLS}" ]]; then
    printf 'STALL_DETECTED polls=%s seconds=%s\n' "$stall_count" "$((stall_count * POLL_SEC))" >&2
    if [[ "${DID_NUDGE}" -ne 1 ]]; then
      DID_NUDGE=1
      nudge_ui
    fi
  fi

  prev_copy_bytes="${copy_bytes}"
  prev_copy_sha="${copy_sha}"
  prev_shot_sha="${shot_sha}"

  line="$(extract_answer_line "$TMP")"
  if [[ -n "${line:-}" ]]; then
    printf '%s\n' "$line"
    exit 0
  fi
  if [[ "$i" -eq "$NUDGE_AT" ]] && [[ "${DID_NUDGE}" -ne 1 ]]; then
    DID_NUDGE=1
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
