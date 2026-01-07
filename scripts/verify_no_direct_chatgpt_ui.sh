#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT"

matches=""
if command -v rg >/dev/null 2>&1; then
  matches="$(rg -n --glob '*.py' --glob '!lucy_agents/chatgpt_bridge.py' --glob '!scripts/**' --glob '!external/nodo-de-voz-modular-de-lucy/**' \
    -e 'chatgpt_ui_ask_x11\.sh' -e 'lucy_chatgpt_ask\.sh' -e 'x11_host_exec\.sh' . || true)"
else
  matches="$(grep -RIn --include='*.py' --exclude='lucy_agents/chatgpt_bridge.py' --exclude-dir='scripts' --exclude-dir='external/nodo-de-voz-modular-de-lucy' \
    -e 'chatgpt_ui_ask_x11\.sh' -e 'lucy_chatgpt_ask\.sh' -e 'x11_host_exec\.sh' . || true)"
fi

if [[ -n "${matches}" ]]; then
  echo "ERROR: direct ChatGPT UI calls detected in Python:" >&2
  printf '%s\n' "${matches}" >&2
  exit 2
fi

echo "VERIFY_NO_DIRECT_CHATGPT_UI_OK"
