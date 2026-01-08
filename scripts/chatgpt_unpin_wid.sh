#!/usr/bin/env bash
set -euo pipefail

PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin_${PROFILE_NAME}}"
export CHATGPT_WID_PIN_FILE="$PIN_FILE"
if [[ -f "${PIN_FILE}" ]]; then
  rm -f "${PIN_FILE}"
fi

printf 'UNPIN_OK\n'
