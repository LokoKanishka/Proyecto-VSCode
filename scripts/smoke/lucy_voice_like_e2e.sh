#!/usr/bin/env bash
set -euo pipefail
ROOT="$HOME/Lucy_Workspace/Proyecto-VSCode"
cd "$ROOT" || exit 1

export X11_FILE_IPC_DIR="$ROOT/diagnostics/x11_file_ipc"
source "$ROOT/scripts/x11_env.sh" || true
export CHATGPT_BRIDGE_PROFILE_DIR="${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chatgpt_bridge_profile}"

LOG=/tmp/voice_like_e2e_last.log
: >"$LOG"

log(){ printf '%s\n' "$*" | tee -a "$LOG"; }

E2E_ID="$(date +%s)"
log "E2E_ID=$E2E_ID"

# watchdog anti-secuestro (mata loops si algo se cuelga feo)
( sleep 110; /home/lucy-ubuntu/Lucy_Workspace/Proyecto-VSCode/scripts/smoke/lucy_panic.sh >/dev/null 2>&1 || true ) &
WD_PID=$!

timeout 8s "$ROOT/scripts/chatgpt_bridge_ensure.sh" >/dev/null 2>&1 || true
WID="$("$ROOT/scripts/chatgpt_get_wid.sh" 2>/dev/null || true)"
if [[ -z "${WID:-}" ]]; then
  log "ERROR: no pude resolver CHATGPT_WID_HEX"
  kill "$WD_PID" >/dev/null 2>&1 || true
  log "RC=2"
  log "DONE"
  exit 2
fi
export CHATGPT_WID_HEX="$WID"
log "CHATGPT_WID_HEX=$CHATGPT_WID_HEX"

log "== 1) ASK1 (60s): pedir comando SAFE (solo echo) =="
ANS1="$(timeout 60s "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: echo LUCY_CMD_OK_${E2E_ID}" 2>/tmp/voice_like_ask1.err || true)"
log "ASK1_ANS=$ANS1"

if [[ -z "${ANS1:-}" ]]; then
  log "== 1b) ASK1 RETRY (60s) =="
  ANS1="$(timeout 60s "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: echo LUCY_CMD_OK_${E2E_ID}" 2>/tmp/voice_like_ask1b.err || true)"
  log "ASK1_ANS_RETRY=$ANS1"
fi

# parse CMD (lo que va después del ":")
CMD="${ANS1#*:}"
CMD="${CMD#"${CMD%%[![:space:]]*}"}"

if ! printf '%s' "$CMD" | grep -Eq "^echo LUCY_CMD_OK_${E2E_ID}$"; then
  log "ERROR: comando no permitido o mal formado: [$CMD]"
  tail -n 80 /tmp/voice_like_ask1.err 2>/dev/null || true
  tail -n 80 /tmp/voice_like_ask1b.err 2>/dev/null || true
  kill "$WD_PID" >/dev/null 2>&1 || true
  log "RC=3"
  log "DONE"
  exit 3
fi
log "CMD_OK=$CMD"

log "== 2) HOST exec (command) =="
OUT="$("$ROOT/scripts/x11_host_exec.sh" "bash -lc \"$CMD\"" | tail -n 1 | tr -d '\r')"
log "HOST_OUT_LINE=$OUT"

log "== 3) SEND output a ChatGPT =="
timeout 15s "$ROOT/scripts/chatgpt_ui_send_x11.sh" "LUCY_CMD_OUT_${E2E_ID}: $OUT" >/dev/null 2>&1 || true
log "SENT_OUT=1"

log "== 4) ASK2 (45s): confirmar OK =="
ANS2="$(timeout 45s "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: OK" 2>/tmp/voice_like_ask2.err || true)"
log "ASK2_ANS=$ANS2"

if [[ -z "${ANS2:-}" ]]; then
  log "== 4b) ASK2 RETRY (35s) =="
  ANS2="$(timeout 35s "$ROOT/scripts/chatgpt_ui_ask_x11.sh" "Respondé exactamente con: OK" 2>/tmp/voice_like_ask2b.err || true)"
  log "ASK2_ANS_RETRY=$ANS2"
fi

kill "$WD_PID" >/dev/null 2>&1 || true

if printf '%s\n' "$ANS2" | grep -Eq '^LUCY_ANSWER_[0-9_]+: OK$'; then
  log "RC=0"
else
  log "RC=4"
fi
log "DONE"
