#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
ASK="${ROOT}/scripts/lucy_chatgpt_ask.sh"

prompt="Respondé exactamente con: OK"

: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT

check_answer_ok() {
  local line="$1"
  if [[ "${line}" =~ :[[:space:]]*OK$ ]]; then
    return 0
  fi
  if [[ "${line}" =~ [[:space:]]OK$ ]]; then
    return 0
  fi
  return 1
}

for i in 1 2 3; do
  tmp_err="$(mktemp)"
  set +e
  out="$("${ASK}" "${prompt}" 2> >(tee "${tmp_err}" >&2))"
  rc=$?
  set -e

  if [[ "${rc}" -ne 0 ]]; then
    echo "ERROR: ask ${i} failed (rc=${rc})" >&2
    exit 1
  fi

  if [[ "${out}" != ANSWER_LINE=* ]]; then
    echo "ERROR: ask ${i} output malformed: '${out}'" >&2
    exit 1
  fi

  answer_line="${out#ANSWER_LINE=}"
  if ! check_answer_ok "${answer_line}"; then
    echo "ERROR: ask ${i} did not end with OK: '${answer_line}'" >&2
    exit 1
  fi

  forensics_dir="$(sed -n 's/^FORENSICS_DIR=//p' "${tmp_err}" | tail -n 1)"
  if [[ -z "${forensics_dir}" ]]; then
    echo "ERROR: ask ${i} missing FORENSICS_DIR" >&2
    exit 1
  fi
  if [[ ! -d "${forensics_dir}" ]]; then
    echo "ERROR: ask ${i} FORENSICS_DIR not found: ${forensics_dir}" >&2
    exit 1
  fi
  for f in request.txt stdout.txt stderr.txt meta.env; do
    if [[ ! -f "${forensics_dir}/${f}" ]]; then
      echo "ERROR: ask ${i} missing forensics file: ${forensics_dir}/${f}" >&2
      exit 1
    fi
  done

  echo "${out}"

  rm -f "${tmp_err}"
 done

echo "VERIFY_CHATGPT_BRIDGE_API_OK"
