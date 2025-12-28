#!/usr/bin/env bash
set -euo pipefail
pkill -f 'chatgpt_ui_ask_x11.sh' || true
pkill -f 'chatgpt_copy_chat_text.sh' || true
pkill -f '/scripts/x11_wrap/xdotool' || true
pkill -x xdotool || true
echo PANIC_OK
