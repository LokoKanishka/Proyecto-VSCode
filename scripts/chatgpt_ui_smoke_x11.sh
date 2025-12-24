#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

env -i HOME="$HOME" USER="$USER" PATH="$PATH" bash -c "
set -euo pipefail
cd '$ROOT' || exit 1
. ./scripts/x11_env.sh

WID=\"\$(./scripts/chatgpt_get_wid.sh)\"
echo \"DETECTED_WID=\$WID\" 1>&2

CHATGPT_WID_HEX=\"\$WID\" ./scripts/chatgpt_ui_ask_x11.sh \"Respondé exactamente con: OK\" 1>&2
"
echo "SMOKE_OK" 1>&2
