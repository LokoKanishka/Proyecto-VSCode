#!/usr/bin/env bash
set -euo pipefail

list_out="$(python3 -m lucy_agents.action_router --list)"
if ! grep -qx "echo" <<<"${list_out}"; then
  echo "ERROR: echo missing" >&2
  exit 1
fi
if ! grep -qx "chatgpt_ask" <<<"${list_out}"; then
  echo "ERROR: chatgpt_ask missing" >&2
  exit 1
fi
if ! grep -qx "summarize_forense" <<<"${list_out}"; then
  echo "ERROR: summarize_forense missing" >&2
  exit 1
fi
if ! grep -qx "daily_plan" <<<"${list_out}"; then
  echo "ERROR: daily_plan missing" >&2
  exit 1
fi

desc="$(python3 -m lucy_agents.action_router --describe chatgpt_ask)"
python3 - <<'PY' "$desc"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
req = obj.get("payload", {}).get("required") or []
if "prompt" not in req:
    raise SystemExit(1)
PY

echo "VERIFY_ACTION_ROUTER_INTROSPECTION_OK"
