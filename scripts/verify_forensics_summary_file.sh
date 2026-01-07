#!/usr/bin/env bash
set -euo pipefail

: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT

prompt="Respondé exactamente con: OK"

tmp_err="$(mktemp)"
set +e
out="$(python3 -m lucy_agents.chatgpt_bridge "${prompt}" 2> >(tee "${tmp_err}" >&2))"
rc=$?
set -e

if [[ "${rc}" -ne 0 ]]; then
  echo "ERROR: bridge failed (rc=${rc})" >&2
  exit 1
fi

if [[ "${out}" != "OK" ]]; then
  echo "ERROR: unexpected output: '${out}'" >&2
  exit 1
fi

forensics_dir="$(sed -n 's/^FORENSICS_DIR=//p' "${tmp_err}" | tail -n 1)"
if [[ -z "${forensics_dir}" ]]; then
  echo "ERROR: missing FORENSICS_DIR" >&2
  exit 1
fi

summary_path="${forensics_dir}/summary.json"
if [[ ! -f "${summary_path}" ]]; then
  echo "ERROR: summary.json missing: ${summary_path}" >&2
  exit 1
fi

python3 - <<'PY' "${summary_path}"
import json
import sys
path = sys.argv[1]
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)
if data.get("signal") != "OK":
    raise SystemExit(1)
if not data.get("answer_line"):
    raise SystemExit(2)
PY

echo "VERIFY_FORENSICS_SUMMARY_FILE_OK"
