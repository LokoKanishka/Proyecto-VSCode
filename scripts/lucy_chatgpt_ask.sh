#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

PROMPT="${1:-}"
if [[ -z "${PROMPT:-}" ]]; then
  echo "ERROR: usage: $0 <prompt>" >&2
  exit 2
fi

LUCY_CHATGPT_TIMEOUT_SEC="${LUCY_CHATGPT_TIMEOUT_SEC:-180}"
LUCY_CHATGPT_RETRIES="${LUCY_CHATGPT_RETRIES:-2}"
if ! [[ "${LUCY_CHATGPT_RETRIES}" =~ ^[0-9]+$ ]]; then
  LUCY_CHATGPT_RETRIES=2
fi
if [[ "${LUCY_CHATGPT_RETRIES}" -lt 1 ]]; then
  LUCY_CHATGPT_RETRIES=1
fi

now_ms() {
  local ms
  ms="$(date +%s%3N 2>/dev/null || true)"
  if ! [[ "${ms}" =~ ^[0-9]+$ ]]; then
    ms=$(( $(date +%s) * 1000 ))
  fi
  printf '%s' "${ms}"
}

TODAY="$(date +%F)"
EPOCH="$(date +%s)"
RAND="${RANDOM}"
FORENSICS_DIR="/tmp/lucy_chatgpt_bridge/${TODAY}/REQ_${EPOCH}_${RAND}"
mkdir -p "${FORENSICS_DIR}"

printf '%s' "${PROMPT}" > "${FORENSICS_DIR}/request.txt"
: > "${FORENSICS_DIR}/stdout.txt"
: > "${FORENSICS_DIR}/stderr.txt"
: > "${FORENSICS_DIR}/meta.env"

START_MS="$(now_ms)"
ANSWER_LINE=""

attempt=0
while [[ "${attempt}" -lt "${LUCY_CHATGPT_RETRIES}" ]]; do
  attempt=$((attempt + 1))
  tmp_out="$(mktemp)"
  tmp_err="$(mktemp)"

  set +e
  CHATGPT_ASK_TIMEOUT_SEC="${LUCY_CHATGPT_TIMEOUT_SEC}" \
    "${ROOT}/scripts/chatgpt_ui_ask_x11.sh" "${PROMPT}" \
    >"${tmp_out}" 2>"${tmp_err}"
  rc=$?
  set -e

  {
    echo "=== ATTEMPT ${attempt} ==="
    cat "${tmp_out}"
  } >> "${FORENSICS_DIR}/stdout.txt"

  {
    echo "=== ATTEMPT ${attempt} ==="
    cat "${tmp_err}"
  } >> "${FORENSICS_DIR}/stderr.txt"

  line="$(grep -m1 -E '^LUCY_ANSWER_' "${tmp_out}" || true)"
  if [[ "${rc}" -eq 0 ]] && [[ -n "${line}" ]]; then
    ANSWER_LINE="${line}"
    rm -f "${tmp_out}" "${tmp_err}"
    break
  fi

  rm -f "${tmp_out}" "${tmp_err}"
  ANSWER_LINE=""
  sleep 0.2
 done

END_MS="$(now_ms)"
ELAPSED_MS=$(( END_MS - START_MS ))
if [[ "${ELAPSED_MS}" -lt 0 ]]; then
  ELAPSED_MS=0
fi

token=""
if [[ -n "${ANSWER_LINE}" ]]; then
  token="$(printf '%s' "${ANSWER_LINE}" | sed -n 's/^LUCY_ANSWER_\([^:]*\):.*/\1/p')"
fi

if [[ -n "${token}" ]]; then
  echo "TOKEN=${token}" >> "${FORENSICS_DIR}/meta.env"
fi
if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
  echo "WID=${CHATGPT_WID_HEX}" >> "${FORENSICS_DIR}/meta.env"
fi
echo "ELAPSED_MS=${ELAPSED_MS}" >> "${FORENSICS_DIR}/meta.env"

find_path_in_logs() {
  local key="$1"
  local path=""
  path="$(grep -h -m1 -E "${key}=[^[:space:]]+" "${FORENSICS_DIR}/stdout.txt" "${FORENSICS_DIR}/stderr.txt" 2>/dev/null | head -n 1 | sed 's/.*=//')"
  printf '%s' "${path}"
}

copy_if_present() {
  local path="$1"
  local dest="$2"
  if [[ -n "${path}" ]] && [[ -f "${path}" ]]; then
    cp -f "${path}" "${dest}"
  fi
}

copy_path="${COPY_PATH:-${FAIL_COPY_PATH:-}}"
shot_path="${SCREENSHOT_PATH:-${FAIL_SHOT_PATH:-${SHOT_PATH:-}}}"

if [[ -z "${copy_path}" ]]; then
  copy_path="$(find_path_in_logs 'COPY_PATH')"
fi
if [[ -z "${copy_path}" ]]; then
  copy_path="$(find_path_in_logs 'FAIL_COPY_PATH')"
fi
if [[ -z "${shot_path}" ]]; then
  shot_path="$(find_path_in_logs 'FAIL_SHOT_PATH')"
fi
if [[ -z "${shot_path}" ]]; then
  shot_path="$(find_path_in_logs 'SHOT_PATH')"
fi
if [[ -z "${shot_path}" ]]; then
  shot_path="$(find_path_in_logs 'SCREENSHOT_PATH')"
fi

copy_if_present "${copy_path}" "${FORENSICS_DIR}/copy.txt"
copy_if_present "${shot_path}" "${FORENSICS_DIR}/screenshot.png"

printf 'FORENSICS_DIR=%s\n' "${FORENSICS_DIR}" >&2
printf 'ELAPSED_MS=%s\n' "${ELAPSED_MS}" >&2

if [[ -z "${ANSWER_LINE}" ]]; then
  exit 1
fi

printf 'ANSWER_LINE=%s\n' "${ANSWER_LINE}"
