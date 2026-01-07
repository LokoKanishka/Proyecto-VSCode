#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="${ROOT}/docs/ACTIONS.md"

actions="$(python3 -m lucy_agents.action_router --list)"

{
  echo "# Lucy Actions"
  echo
  echo "Generated from action_router --describe."
  echo
  echo "| Action | Path | Required |"
  echo "| --- | --- | --- |"

  while IFS= read -r action; do
    [[ -z "${action}" ]] && continue
    desc="$(python3 -m lucy_agents.action_router --describe "${action}")"
    required="$(python3 - <<'PY' "$desc"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
req = obj.get("payload", {}).get("required") or []
print(", ".join(req))
PY
)"
    path="$(python3 - <<'PY' "$desc"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
print(obj.get("path") or "-")
PY
)"
    echo "| ${action} | ${path} | ${required:- -} |"
  done <<< "${actions}"

  echo
  while IFS= read -r action; do
    [[ -z "${action}" ]] && continue
    desc="$(python3 -m lucy_agents.action_router --describe "${action}")"
    echo "## ${action}"
    echo
    echo "\`\`\`json"
    echo "${desc}"
    echo "\`\`\`"
    echo
  done <<< "${actions}"
} > "${OUT}"

echo "GEN_ACTIONS_MD_OK"
