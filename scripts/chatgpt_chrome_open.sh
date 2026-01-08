#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

CHROME_BIN="${CHATGPT_CHROME_BIN:-google-chrome}"
PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-}"
BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-}"
URL="${1:-${CHATGPT_OPEN_URL:-https://chat.openai.com/}}"

args=()
if [[ -n "${PROFILE_DIR:-}" ]]; then
  args+=(--user-data-dir="${PROFILE_DIR}")
fi
if [[ -n "${BRIDGE_CLASS:-}" ]]; then
  args+=(--class "${BRIDGE_CLASS}")
fi
args+=(--no-first-run --no-default-browser-check --new-window "${URL}")

cmd="$CHROME_BIN"
for arg in "${args[@]}"; do
  cmd+=" $(printf '%q' "${arg}")"
done

"$HOST_EXEC" "bash -lc '${cmd} >/dev/null 2>&1 & disown'" >/dev/null 2>&1 || true
