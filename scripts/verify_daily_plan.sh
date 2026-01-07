#!/usr/bin/env bash
set -euo pipefail

: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT

restore_paths=()
restore_targets=()

restore_files() {
  local i
  for i in "${!restore_paths[@]}"; do
    if [[ -e "${restore_paths[$i]}" ]]; then
      mv -f "${restore_paths[$i]}" "${restore_targets[$i]}" || true
    fi
  done
}
trap restore_files EXIT

move_if_exists() {
  local src="$1"
  if [[ -f "${src}" ]]; then
    local tmp
    tmp="/tmp/lucy_daily_plan_backup_$(date +%s%N)"
    mv "${src}" "${tmp}"
    restore_paths+=("${tmp}")
    restore_targets+=("${src}")
  fi
}

# Case 1: offline without file
unset LUCY_DAILY_PLAN_FILE
move_if_exists "$HOME/.local/share/lucy/daily_plan.md"
move_if_exists "./docs/daily_plan.md"

out1="$(python3 -m lucy_agents.action_router daily_plan '{}')"
python3 - <<'PY' "$out1"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
if not obj.get("ok"):
    raise SystemExit(1)
result = obj.get("result", {})
source = result.get("source")
if source not in ("OFFLINE", "FILE"):
    raise SystemExit(2)
final_plan = result.get("final_plan") or ""
if len(final_plan) <= 50:
    raise SystemExit(3)
PY

# Case 2: file source
mkdir -p /tmp/lucy_daily
printf '%s\n' "PLAN BASE TEST" > /tmp/lucy_daily/plan.md
out2="$(LUCY_DAILY_PLAN_FILE=/tmp/lucy_daily/plan.md python3 -m lucy_agents.action_router daily_plan '{}')"
python3 - <<'PY' "$out2"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
if not obj.get("ok"):
    raise SystemExit(1)
result = obj.get("result", {})
base_plan = result.get("base_plan") or ""
if "PLAN BASE TEST" not in base_plan:
    raise SystemExit(2)
PY

# Case 3: chatgpt enhancement
out3="$(LUCY_CHATGPT_AUTO_CHAT=1 python3 -m lucy_agents.action_router daily_plan '{"use_chatgpt":true,"prompt_hint":"priorizar programacion"}')"
python3 - <<'PY' "$out3"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
if not obj.get("ok"):
    raise SystemExit(1)
result = obj.get("result", {})
if result.get("chatgpt_used") is not True:
    raise SystemExit(2)
final_plan = result.get("final_plan") or ""
if len(final_plan) <= 50:
    raise SystemExit(3)
PY

echo "VERIFY_DAILY_PLAN_OK"
