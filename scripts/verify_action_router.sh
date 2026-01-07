#!/usr/bin/env bash
set -euo pipefail

: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT

have_jq=0
if command -v jq >/dev/null 2>&1; then
  have_jq=1
fi

out="$(python3 -m lucy_agents.action_router echo '{"x":1}')"
if [[ "${have_jq}" -eq 1 ]]; then
  echo "${out}" | jq -e '.ok==true and .result.x==1' >/dev/null
else
  python3 - <<'PY' "$out"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
if not (obj.get("ok") is True and obj.get("result", {}).get("x") == 1):
    raise SystemExit(1)
PY
fi

out="$(python3 -m lucy_agents.action_router chatgpt_ask '{"prompt":"Respondé exactamente con: OK"}')"
if [[ "${have_jq}" -eq 1 ]]; then
  echo "${out}" | jq -e '.ok==true and .result.answer_text=="OK"' >/dev/null
else
  python3 - <<'PY' "$out"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
if not (obj.get("ok") is True and obj.get("result", {}).get("answer_text") == "OK"):
    raise SystemExit(1)
PY
fi

echo "VERIFY_ACTION_ROUTER_OK"
