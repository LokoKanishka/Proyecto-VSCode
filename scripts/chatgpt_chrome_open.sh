#!/usr/bin/env bash
set -euo pipefail


ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
THREAD_LOADER="$ROOT/scripts/chatgpt_thread_url_load.sh"
OPEN_PROFILE="$ROOT/scripts/chrome_open_profile_url.sh"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
ENSURE_URL="$ROOT/scripts/chrome_ensure_url_in_window.sh"

PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
CHROME_BIN="${CHATGPT_CHROME_BIN:-google-chrome}"
PROFILE_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-}"
BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-}"
THREAD_URL="$("$THREAD_LOADER" 2>/dev/null || true)"
OPEN_URL="${CHATGPT_OPEN_URL:-https://chatgpt.com/}"
URL="${1:-${THREAD_URL:-$OPEN_URL}}"

if [ -z "${URL:-}" ]; then
  echo "ERROR_NO_URL" >&2
  exit 2
fi
if ! printf '%s' "$URL" | grep -Eq '^(https?://|file://)'; then
  echo "ERROR_BAD_URL: <$URL>" >&2
  exit 2
fi

if [ -n "${CHROME_WID_HEX:-}" ] && [ -x "$ENSURE_URL" ]; then
  if "$ENSURE_URL" "$CHROME_WID_HEX" "$URL" 8 >/dev/null 2>&1; then
    echo "OK_OPEN_WID=$CHROME_WID_HEX URL=$URL"
    exit 0
  fi
  echo "ERROR_OPEN_WID URL_LOCK_FAILED wid=$CHROME_WID_HEX" >&2
  exit 3
fi

if [[ -n "${PROFILE_DIR:-}" || "${CHATGPT_TARGET}" == "free" || "${CHATGPT_TARGET}" == "dummy" ]]; then
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
else
  CHROME_CLASS="$BRIDGE_CLASS" \
  CHROME_EXTRA_ARGS="--no-first-run --no-default-browser-check --disable-session-crashed-bubble" \
    "$OPEN_PROFILE" "$PROFILE_NAME" "$URL" >/dev/null 2>&1 || true
fi
