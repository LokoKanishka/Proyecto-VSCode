#!/usr/bin/env bash
set -euo pipefail

fake_dir="/tmp/lucy_forense_fake"
rm -rf "${fake_dir}"
mkdir -p "${fake_dir}"

cat <<'TXT' > "${fake_dir}/request.txt"
PROMPT line 1
PROMPT line 2
TXT

cat <<'TXT' > "${fake_dir}/stderr.txt"
STALL_DETECTED polls=12 seconds=24
WATCHDOG_STEP=RELOAD t_ms=1234
COPY_BYTES=431 COPY_CHOSEN=messages
ANSWER_LINE=LUCY_ANSWER_123: OK
TXT

cat <<'TXT' > "${fake_dir}/stdout.txt"
LUCY_ANSWER_123: OK
TXT

out="$(python3 -m lucy_agents.action_router summarize_forense "{\"dir\":\"${fake_dir}\"}")"

python3 - <<'PY' "$out"
import json
import sys
raw = sys.argv[1]
obj = json.loads(raw)
if obj.get("ok") is not True:
    raise SystemExit(1)
result = obj.get("result", {})
steps = result.get("watchdog_steps") or []
if "RELOAD" not in steps:
    raise SystemExit(2)
if result.get("signal") != "OK":
    raise SystemExit(3)
PY

echo "VERIFY_FORENSICS_SUMMARY_OK"
