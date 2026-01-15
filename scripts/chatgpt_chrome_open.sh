#!/usr/bin/env bash
set -euo pipefail


ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
THREAD_LOADER="$ROOT/scripts/chatgpt_thread_url_load.sh"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

CHROME_BIN="${CHATGPT_CHROME_BIN:-google-chrome}"
PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-}"
BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-}"
THREAD_URL="$(${THREAD_LOADER} 2>/dev/null || echo ${CHATGPT_OPEN_URL:-https://chatgpt.com/})"
OPEN_URL="${CHATGPT_OPEN_URL:-https://chatgpt.com/}"
URL="${1:-${THREAD_URL:-$OPEN_URL}}"

args=()
if [[ -n "${PROFILE_DIR:-}" ]]; then
  args+=(--user-data-dir="${PROFILE_DIR}")
fi
if [[ -n "${BRIDGE_CLASS:-}" ]]; then
  args+=(--class="${BRIDGE_CLASS}")
fi
args+=(--no-first-run --no-default-browser-check --disable-session-crashed-bubble --new-window "${URL}")

cmd="$CHROME_BIN"
for arg in "${args[@]}"; do
  cmd+=" $(printf '%q' "${arg}")"
done

"$HOST_EXEC" "bash -lc '${cmd} >/dev/null 2>&1 & disown'" >/dev/null 2>&1 || true
