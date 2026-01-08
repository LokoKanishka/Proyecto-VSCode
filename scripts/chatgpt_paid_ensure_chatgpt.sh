#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
THREAD_ENSURE="$ROOT/scripts/chatgpt_paid_ensure_test_thread.sh"

CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
if [[ "${CHATGPT_TARGET}" != "paid" ]]; then
  echo "ERROR: chatgpt_paid_ensure_chatgpt.sh requiere CHATGPT_TARGET=paid" >&2
  exit 2
fi

DEFAULT_FREE_DIR="$HOME/.cache/lucy_chrome_chatgpt_free"
FREE_DIR="${CHATGPT_FREE_PROFILE_DIR:-${CHATGPT_CHROME_USER_DATA_DIR:-$DEFAULT_FREE_DIR}}"
PAID_PID_HINT="${CHATGPT_PAID_PID_HINT:-}"
TIMEOUT_S="${CHATGPT_ENSURE_TIMEOUT_S:-40}"
LOG_PATH="${CHATGPT_PAID_ENSURE_LOG:-/tmp/paid_ensure_chatgpt.log}"

log() {
  printf '%s\n' "$*" >>"$LOG_PATH"
}

mkdir -p "$(dirname "$LOG_PATH")"
: >"$LOG_PATH"
log "PAID_ENSURE_START free_dir=${FREE_DIR} timeout_s=${TIMEOUT_S}"

host_script="$(mktemp /tmp/lucy_paid_ensure_host.XXXX.sh)"
cat > "$host_script" <<'HOST'
#!/usr/bin/env bash
set -euo pipefail
wm_out="$(wmctrl -lp 2>/dev/null || true)"

is_chrome_pid() {
  local pid="$1" args
  args="$(ps -o args= -p "$pid" 2>/dev/null || true)"
  [[ -n "${args}" ]] || return 1
  [[ "${args}" == *"/opt/google/chrome/chrome"* ]] || [[ "${args}" == *"google-chrome"* ]] || [[ "${args}" == *"chromium"* ]] || return 1
  if [[ -n "${FREE_DIR}" ]] && [[ "${args}" == *"--user-data-dir=${FREE_DIR}"* ]]; then
    return 1
  fi
  if [[ -n "${FREE_DIR}" ]] && [[ "${args}" == *"--user-data-dir ${FREE_DIR}"* ]]; then
    return 1
  fi
  return 0
}

pid_has_window() {
  local pid="$1"
  awk -v pid="$pid" '$3==pid {found=1} END{exit !found}' <<< "$wm_out"
}

pick_pid() {
  local pid
  if [[ -n "${PID_HINT:-}" ]]; then
    if pid_has_window "${PID_HINT}" && is_chrome_pid "${PID_HINT}"; then
      echo "${PID_HINT}"
      return 0
    fi
  fi
  for pid in $(printf "%s\n" "$wm_out" | awk '{print $3}' | sort -u); do
    if pid_has_window "$pid" && is_chrome_pid "$pid"; then
      echo "$pid"
      return 0
    fi
  done
  return 1
}

pid="$(pick_pid || true)"
if [[ -z "${pid}" ]]; then
  echo "PID="
  exit 0
fi
wid="$(awk -v pid="$pid" '$3==pid {print $1; exit}' <<< "$wm_out")"
echo "PID=${pid}"
echo "WID=${wid}"
HOST
chmod +x "$host_script"

free_q="$(printf '%q' "$FREE_DIR")"
hint_q="$(printf '%q' "$PAID_PID_HINT")"
paid_info="$("$HOST_EXEC" "bash -lc 'FREE_DIR=${free_q} PID_HINT=${hint_q} ${host_script}'" 2>/dev/null || true)"
rm -f "$host_script" 2>/dev/null || true

PAID_PID="$(awk -F= '/^PID=/{print $2}' <<< "$paid_info" | tail -n 1)"
BASE_WID="$(awk -F= '/^WID=/{print $2}' <<< "$paid_info" | tail -n 1)"
if [[ -z "${PAID_PID:-}" ]]; then
  log "ERROR: no paid PID found"
  log "paid_info:"
  log "$paid_info"
  echo "ERROR: no paid PID found" >&2
  echo "PAID_ENSURE_LOG=$LOG_PATH" >&2
  exit 3
fi

if [[ -z "${BASE_WID:-}" ]]; then
  log "ERROR: no base WID for paid PID=${PAID_PID}"
  echo "ERROR: no base WID for paid PID=${PAID_PID}" >&2
  echo "PAID_ENSURE_LOG=$LOG_PATH" >&2
  exit 3
fi

log "PAID_PID=${PAID_PID} BASE_WID=${BASE_WID}"

BASE_WID_DEC="$(printf "%d" "$BASE_WID" 2>/dev/null || echo 0)"
if [[ "${BASE_WID_DEC}" -gt 0 ]]; then
  "$HOST_EXEC" "wmctrl -ia ${BASE_WID}" >/dev/null 2>&1 || true
  "$HOST_EXEC" "xdotool windowactivate --sync ${BASE_WID_DEC}" >/dev/null 2>&1 || true
  "$HOST_EXEC" "sleep 0.2" >/dev/null 2>&1 || true
  "$HOST_EXEC" "xdotool key --window ${BASE_WID_DEC} ctrl+l" >/dev/null 2>&1 || true
  "$HOST_EXEC" "sleep 0.05" >/dev/null 2>&1 || true
  "$HOST_EXEC" "xdotool type --window ${BASE_WID_DEC} 'https://chatgpt.com/'" >/dev/null 2>&1 || true
  "$HOST_EXEC" "xdotool key --window ${BASE_WID_DEC} Return" >/dev/null 2>&1 || true
fi

for _ in $(seq 1 "$TIMEOUT_S"); do
  wm_out="$("$HOST_EXEC" "wmctrl -lp" 2>/dev/null || true)"
  chat_wid="$(awk -v pid="$PAID_PID" '$3==pid {print $1 "\t" $0}' <<< "$wm_out" | grep -i "ChatGPT" | head -n 1 | awk '{print $1}' || true)"
  if [[ -n "${chat_wid:-}" ]]; then
    log "PAID_CHATGPT_WID=${chat_wid}"
    printf 'PAID_CHATGPT_WID=%s\n' "$chat_wid"
    printf 'PAID_CHATGPT_PID=%s\n' "$PAID_PID"
    if [[ -x "$THREAD_ENSURE" ]]; then
      if ! CHATGPT_PAID_ENSURE_CALLER=1 "$THREAD_ENSURE" >/dev/null 2>&1; then
        log "ERROR: ensure_test_thread failed"
        echo "ERROR: ensure_test_thread failed" >&2
        echo "PAID_ENSURE_LOG=$LOG_PATH" >&2
        exit 5
      fi
    fi
    exit 0
  fi
  sleep 1
done

log "ERROR: timeout waiting for ChatGPT tab (pid=${PAID_PID})"
log "wmctrl_lp:"
log "$wm_out"
log "ps_args:"
log "$("$HOST_EXEC" "ps -o args= -p ${PAID_PID}" 2>/dev/null || true)"

echo "ERROR: timeout waiting for ChatGPT tab (pid=${PAID_PID})" >&2
echo "PAID_ENSURE_LOG=$LOG_PATH" >&2
exit 4
