#!/usr/bin/env bash
set -euo pipefail

CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin_${CHATGPT_TARGET}}"
ensure_pin_file() {
  local f="$1"
  local dir
  dir="$(dirname "$f")"
  mkdir -p "$dir" 2>/dev/null || true
  if [[ -e "$f" ]]; then
    dd if=/dev/null of="$f" 2>/dev/null || return 1
  else
    local tmp
    tmp="$(mktemp "$dir/.pinwrite.XXXX" 2>/dev/null)" || return 1
    rm -f "$tmp" 2>/dev/null || true
  fi
  return 0
}
if ! ensure_pin_file "$PIN_FILE"; then
  PIN_FILE="/tmp/lucy_chatgpt_wid_pin_${CHATGPT_TARGET}"
  mkdir -p "$(dirname "$PIN_FILE")" 2>/dev/null || true
  echo "WARN: PIN_FILE not writable, using ${PIN_FILE}" >&2
fi
export CHATGPT_WID_PIN_FILE="$PIN_FILE"
if [[ -f "${PIN_FILE}" ]]; then
  rm -f "${PIN_FILE}"
fi

printf 'UNPIN_OK\n'
