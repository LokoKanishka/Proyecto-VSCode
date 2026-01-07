#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin}"

if [[ -f "${PIN_FILE}" ]]; then
  export CHATGPT_WID_PIN_ONLY=1
fi

python3 - <<'PY'
import sys
from lucy_agents.voice_actions import maybe_handle_desktop_intent

text = "preguntale a chatgpt: Responde exactamente con: OK"
result = maybe_handle_desktop_intent(text)
if not isinstance(result, tuple) or len(result) != 2:
    print(f"ERROR: unexpected result: {result!r}", file=sys.stderr)
    sys.exit(1)
handled, answer = result
if not handled:
    print("ERROR: chatgpt request not handled", file=sys.stderr)
    sys.exit(1)
answer_text = (answer or "").strip()
if answer_text != "OK":
    print(f"ERROR: unexpected answer: {answer_text!r}", file=sys.stderr)
    sys.exit(1)
print("OK")
PY

echo "VERIFY_CHATGPT_BRIDGE_INTEGRATION_OK"
