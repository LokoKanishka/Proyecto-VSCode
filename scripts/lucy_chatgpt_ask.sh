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

LOCK_TIMEOUT_SEC="${LUCY_CHATGPT_LOCK_TIMEOUT_SEC:-120}"
LOCK_BASE="/tmp/lucy_chatgpt_bridge"
LOCK_FILE="${LOCK_BASE}/lock"
LOCK_DIR="${LOCK_FILE}.d"
LOCK_HELD=0
LOCK_METHOD=""
LOCK_FD=""

release_lock() {
  if [[ "${LOCK_HELD}" -ne 1 ]]; then
    return 0
  fi
  if [[ "${LOCK_METHOD}" == "flock" ]]; then
    flock -u "${LOCK_FD}" 2>/dev/null || true
    eval "exec ${LOCK_FD}>&-"
  elif [[ "${LOCK_METHOD}" == "lockdir" ]]; then
    rmdir "${LOCK_DIR}" 2>/dev/null || true
  fi
  LOCK_HELD=0
  printf 'LOCK_RELEASED=1\n' >&2
}

acquire_lock() {
  mkdir -p "${LOCK_BASE}"
  local start_ms end_ms now waited_ms waited_sec
  start_ms="$(now_ms)"
  end_ms=$(( start_ms + (LOCK_TIMEOUT_SEC * 1000) ))

  if command -v flock >/dev/null 2>&1; then
    LOCK_METHOD="flock"
    exec {LOCK_FD}>"${LOCK_FILE}"
    if ! flock -w "${LOCK_TIMEOUT_SEC}" "${LOCK_FD}"; then
      waited_sec=$(( LOCK_TIMEOUT_SEC ))
      echo "ERROR: LOCK_TIMEOUT waited=${waited_sec}" >&2
      exit 4
    fi
    waited_ms=$(( $(now_ms) - start_ms ))
    printf 'LOCK_ACQUIRED=1 waited_ms=%s\n' "${waited_ms}" >&2
    LOCK_HELD=1
    return 0
  fi

  LOCK_METHOD="lockdir"
  while true; do
    if mkdir "${LOCK_DIR}" 2>/dev/null; then
      waited_ms=$(( $(now_ms) - start_ms ))
      printf 'LOCK_ACQUIRED=1 waited_ms=%s\n' "${waited_ms}" >&2
      LOCK_HELD=1
      return 0
    fi
    now="$(now_ms)"
    if [[ "${now}" -ge "${end_ms}" ]]; then
      waited_sec=$(( LOCK_TIMEOUT_SEC ))
      echo "ERROR: LOCK_TIMEOUT waited=${waited_sec}" >&2
      exit 4
    fi
    sleep 0.2
  done
}

trap release_lock EXIT
acquire_lock

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
RUN_TMPDIR=""
LAST_TMPDIR=""

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

  attempt_tmpdir="$(sed -n 's/^LUCY_ASK_TMPDIR=//p' "${tmp_err}" | tail -n 1)"
  if [[ -n "${attempt_tmpdir:-}" ]]; then
    LAST_TMPDIR="${attempt_tmpdir}"
  fi

  line="$(grep -m1 -E '^LUCY_ANSWER_' "${tmp_out}" || true)"
  if [[ "${rc}" -eq 0 ]] && [[ -n "${line}" ]]; then
    ANSWER_LINE="${line}"
    if [[ -n "${attempt_tmpdir:-}" ]]; then
      RUN_TMPDIR="${attempt_tmpdir}"
    fi
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

copied_copy_txt=0
copied_screenshot=0
tmpdir="${RUN_TMPDIR:-${LAST_TMPDIR:-}}"
if [[ -n "${tmpdir:-}" ]] && [[ -d "${tmpdir}" ]]; then
  if [[ -f "${tmpdir}/copy.txt" ]]; then
    cp -f "${tmpdir}/copy.txt" "${FORENSICS_DIR}/copy.txt" 2>/dev/null || true
    copied_copy_txt=1
  fi
  if [[ -f "${tmpdir}/copy_1.stderr" ]]; then
    cp -f "${tmpdir}/copy_1.stderr" "${FORENSICS_DIR}/copy_1.stderr" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/copy_2.stderr" ]]; then
    cp -f "${tmpdir}/copy_2.stderr" "${FORENSICS_DIR}/copy_2.stderr" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/copy_2.stderr" ]]; then
    cp -f "${tmpdir}/copy_2.stderr" "${FORENSICS_DIR}/copy.stderr" 2>/dev/null || true
  elif [[ -f "${tmpdir}/copy_1.stderr" ]]; then
    cp -f "${tmpdir}/copy_1.stderr" "${FORENSICS_DIR}/copy.stderr" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/meta.txt" ]]; then
    cp -f "${tmpdir}/meta.txt" "${FORENSICS_DIR}/meta.txt" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/url.txt" ]]; then
    cp -f "${tmpdir}/url.txt" "${FORENSICS_DIR}/url.txt" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/thread_url.txt" ]]; then
    cp -f "${tmpdir}/thread_url.txt" "${FORENSICS_DIR}/thread_url.txt" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/wmctrl_lp.txt" ]]; then
    cp -f "${tmpdir}/wmctrl_lp.txt" "${FORENSICS_DIR}/wmctrl_lp.txt" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/active_wid.txt" ]]; then
    cp -f "${tmpdir}/active_wid.txt" "${FORENSICS_DIR}/active_wid.txt" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/summary.json" ]]; then
    cp -f "${tmpdir}/summary.json" "${FORENSICS_DIR}/summary.json" 2>/dev/null || true
  fi
  if [[ -f "${tmpdir}/fail_screenshot.png" ]]; then
    cp -f "${tmpdir}/fail_screenshot.png" "${FORENSICS_DIR}/screenshot.png" 2>/dev/null || true
    copied_screenshot=1
  fi
fi

printf 'COPIED_COPY_TXT=%s\n' "${copied_copy_txt}" >&2
printf 'COPIED_SCREENSHOT=%s\n' "${copied_screenshot}" >&2

printf 'FORENSICS_DIR=%s\n' "${FORENSICS_DIR}" >&2
printf 'ELAPSED_MS=%s\n' "${ELAPSED_MS}" >&2

summary_path="${FORENSICS_DIR}/summary.json"
if [[ ! -f "${summary_path}" ]]; then
  FINAL_RC=0
  FINAL_STATUS="ok"
  if [[ -z "${ANSWER_LINE}" ]]; then
    FINAL_RC=1
    FINAL_STATUS="fail"
  fi
  TOKEN="${token}"
  export FINAL_RC FINAL_STATUS ANSWER_LINE TOKEN
  python3 - "$summary_path" <<'PY'
import json
import os
import sys

out = sys.argv[1]
def env(key, default=""):
    return os.environ.get(key, default)

data = {
    "token": env("TOKEN", ""),
    "wid": env("CHATGPT_WID_HEX", ""),
    "elapsed_ms": int(env("ELAPSED_MS", "0") or 0),
    "rc": int(env("FINAL_RC", "1") or 1),
    "status": env("FINAL_STATUS", "fail"),
    "answer_line": env("ANSWER_LINE", ""),
    "step": "lucy_chatgpt_ask",
}

with open(out, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=True)
PY
fi

if [[ -z "${ANSWER_LINE}" ]]; then
  exit 1
fi

printf 'ANSWER_LINE=%s\n' "${ANSWER_LINE}"
