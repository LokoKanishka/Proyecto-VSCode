#!/usr/bin/env bash
set -euo pipefail

export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
export CHATGPT_CHROME_USER_DATA_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-$HOME/.cache/lucy_chrome_chatgpt_free}"
export CHATGPT_WID_PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin_${CHATGPT_PROFILE_NAME}}"
export CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"
