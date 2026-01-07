#!/usr/bin/env bash
set -euo pipefail

PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin}"
export CHATGPT_WID_PIN_FILE="$PIN_FILE"
if [[ -f "${PIN_FILE}" ]]; then
  rm -f "${PIN_FILE}"
fi

printf 'UNPIN_OK\n'
