#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ASK="${ROOT}/scripts/lucy_chatgpt_ask.sh"

prompt="Respondé exactamente con: OK"

tmp_err="$(mktemp)"
set +e
out="$(LUCY_CHATGPT_AUTO_CHAT=1 "${ASK}" "${prompt}" 2> >(tee "${tmp_err}" >&2))"
rc=$?
set -e

if [[ "${rc}" -ne 0 ]]; then
  echo "ERROR: ask failed (rc=${rc})" >&2
  exit 1
fi

if [[ "${out}" != ANSWER_LINE=* ]]; then
  echo "ERROR: output malformed: '${out}'" >&2
  exit 1
fi

answer_line="${out#ANSWER_LINE=}"
if [[ ! "${answer_line}" =~ :[[:space:]]*OK$ ]]; then
  echo "ERROR: answer does not end with OK: '${answer_line}'" >&2
  exit 1
fi

forensics_dir="$(sed -n 's/^FORENSICS_DIR=//p' "${tmp_err}" | tail -n 1)"
if [[ -z "${forensics_dir}" ]]; then
  echo "ERROR: missing FORENSICS_DIR" >&2
  exit 1
fi

if [[ ! -f "${forensics_dir}/stderr.txt" ]]; then
  echo "ERROR: missing forensics stderr: ${forensics_dir}/stderr.txt" >&2
  exit 1
fi

if ! grep -q "AUTO_CHAT=1" "${forensics_dir}/stderr.txt"; then
  echo "ERROR: missing AUTO_CHAT=1 in forensics" >&2
  exit 1
fi

if ! grep -q "NEWCHAT_OK=" "${forensics_dir}/stderr.txt"; then
  echo "ERROR: missing NEWCHAT_OK in forensics" >&2
  exit 1
fi

echo "VERIFY_CHATGPT_AUTO_CHAT_OK"
