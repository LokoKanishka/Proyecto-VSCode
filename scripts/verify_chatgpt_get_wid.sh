#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

check_wid() {
  local wid="$1"
  [[ "${wid}" =~ ^0x[0-9a-fA-F]+$ ]]
}

get_title() {
  local wid="$1"
  "$HOST_EXEC" "wmctrl -l | awk '\$1==\"${wid}\" { \$1=\"\"; \$2=\"\"; \$3=\"\"; sub(/^ +/, \"\"); print; exit }'" 2>/dev/null || true
}

list_chrome_wids() {
  "$HOST_EXEC" 'wmctrl -lx' 2>/dev/null | awk '
    {
      wid=$1;
      klass=$3;
      if(tolower(klass) !~ /(google-chrome|chromium)/) next;
      print wid
    }
  '
}

find_new_wid() {
  local before="$1"
  local after="$2"
  comm -13 <(printf '%s\n' "$before" | sort) <(printf '%s\n' "$after" | sort) | tail -n 1
}

wid_is_chrome() {
  local wid="$1"
  local klass
  klass="$("$HOST_EXEC" "wmctrl -lx | awk '\$1==\"${wid}\" {print \$3; exit}'" 2>/dev/null || true)"
  if [[ -z "${klass:-}" ]]; then
    return 1
  fi
  case "${klass,,}" in
    *google-chrome*|*chromium*)
      return 0
      ;;
  esac
  return 1
}

WID1="$($GET_WID)"
if ! check_wid "${WID1}"; then
  echo "ERROR: invalid WID format: ${WID1}" >&2
  exit 1
fi

TITLE1="$(get_title "${WID1}")"
if [[ "${TITLE1}" == *"V.S.Code"* ]]; then
  echo "ERROR: WID title contains V.S.Code: ${TITLE1}" >&2
  exit 1
fi

export CHATGPT_GET_WID_NOOPEN=1

for i in 1 2 3 4 5 6 7 8 9 10; do
  wid="$($GET_WID)"
  if [[ "${wid}" != "${WID1}" ]]; then
    echo "ERROR: unstable WID at run ${i}: got ${wid}, expected ${WID1}" >&2
    exit 1
  fi
  title="$(get_title "${wid}")"
  if [[ "${title}" == *"V.S.Code"* ]]; then
    echo "ERROR: WID title contains V.S.Code at run ${i}: ${title}" >&2
    exit 1
  fi
done

if [[ "${LUCY_SKIP_RECOVERY_TEST:-0}" -ne 1 ]]; then
  unset CHATGPT_GET_WID_NOOPEN
  unset CHATGPT_WID_PIN_ONLY
  TMP_PIN="$(mktemp /tmp/lucy_chatgpt_pin_fake.XXXX.txt)"
  RECOVER_ERR="$(mktemp /tmp/verify_chatgpt_get_wid_recover_err.XXXX.txt)"
  cleanup_pin() {
    rm -f "$TMP_PIN" 2>/dev/null || true
    rm -f "$RECOVER_ERR" 2>/dev/null || true
  }
  trap cleanup_pin EXIT

  printf '0xDEADBEEF\nTITLE=Fake\n' > "$TMP_PIN"
  export CHATGPT_WID_PIN_FILE="$TMP_PIN"

  before_wids="$(list_chrome_wids)"
  "$HOST_EXEC" "bash -lc 'google-chrome --new-window \"https://example.com/\" >/dev/null 2>&1 & disown'" \
    >/dev/null 2>&1 || true
  distractor_wid=""
  for _ in $(seq 1 15); do
    sleep 1
    after_wids="$(list_chrome_wids)"
    distractor_wid="$(find_new_wid "$before_wids" "$after_wids")"
    [[ -n "${distractor_wid:-}" ]] && break
  done
  if [[ -z "${distractor_wid:-}" ]]; then
    echo "ERROR: failed to detect distractor Chrome window" >&2
    exit 1
  fi

  RECOVER_WID="$($GET_WID 2> "$RECOVER_ERR" || true)"
  cat "$RECOVER_ERR" >&2 || true

  if ! check_wid "${RECOVER_WID}"; then
    echo "ERROR: invalid recovered WID format: ${RECOVER_WID}" >&2
    cat "$RECOVER_ERR" >&2 || true
    exit 1
  fi
  if ! grep -q 'PIN_INVALID=1' "$RECOVER_ERR"; then
    echo "ERROR: missing PIN_INVALID=1 in stderr" >&2
    cat "$RECOVER_ERR" >&2 || true
    exit 1
  fi
  if ! grep -q 'PIN_RECOVERED=1' "$RECOVER_ERR"; then
    echo "ERROR: missing PIN_RECOVERED=1 in stderr" >&2
    cat "$RECOVER_ERR" >&2 || true
    exit 1
  fi

  if [[ "${RECOVER_WID}" == "${distractor_wid}" ]]; then
    echo "ERROR: recovered WID matches distractor: ${RECOVER_WID}" >&2
    exit 1
  fi
  if ! wid_is_chrome "${RECOVER_WID}"; then
    echo "ERROR: recovered WID is not chrome: ${RECOVER_WID}" >&2
    exit 1
  fi

  TITLE_RECOVER="$(get_title "${RECOVER_WID}")"
  if [[ "${TITLE_RECOVER}" == *"V.S.Code"* ]]; then
    echo "ERROR: recovered WID title contains V.S.Code: ${TITLE_RECOVER}" >&2
    exit 1
  fi
fi

echo "VERIFY_CHATGPT_GET_WID_OK"
