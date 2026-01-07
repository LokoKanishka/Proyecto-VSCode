#!/usr/bin/env bash
set -euo pipefail

: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT

out_file="$(mktemp)"
err_file="$(mktemp)"

python3 - <<'PY' >"${out_file}" 2>"${err_file}"
import sys
from lucy_agents.voice_actions import maybe_handle_desktop_intent

text = "preguntale a chatgpt: Respondé exactamente con: OK"
result = maybe_handle_desktop_intent(text)
if not isinstance(result, tuple) or len(result) != 2:
    print(f"ERROR: unexpected result: {result!r}", file=sys.stderr)
    sys.exit(1)
handled, answer = result
if not handled:
    print("ERROR: chatgpt request not handled", file=sys.stderr)
    sys.exit(1)
print((answer or "").strip())
PY

if ! grep -xq "OK" "${out_file}"; then
  echo "ERROR: missing OK" >&2
  cat "${out_file}" >&2
  cat "${err_file}" >&2
  exit 1
fi

if ! grep -q "CHATGPT_ROUTER_OK" "${err_file}"; then
  echo "ERROR: missing CHATGPT_ROUTER_OK" >&2
  cat "${out_file}" >&2
  cat "${err_file}" >&2
  exit 1
fi

rm -f "${out_file}" "${err_file}"

echo "VERIFY_VOICE_ACTIONS_ROUTER_OK"
