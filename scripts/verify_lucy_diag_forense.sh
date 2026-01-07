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

out="$(python3 -m lucy_agents.lucy_diag forense "${fake_dir}")"

if ! grep -q "Signal: OK" <<<"${out}"; then
  echo "ERROR: missing Signal: OK" >&2
  echo "${out}" >&2
  exit 1
fi

if ! grep -q "Watchdog:" <<<"${out}"; then
  echo "ERROR: missing Watchdog" >&2
  echo "${out}" >&2
  exit 1
fi

out_json="$(python3 -m lucy_agents.lucy_diag forense "${fake_dir}" --json)"
if [[ "${out_json}" != \{* ]]; then
  echo "ERROR: json output invalid" >&2
  echo "${out_json}" >&2
  exit 1
fi

echo "VERIFY_LUCY_DIAG_FORENSE_OK"
