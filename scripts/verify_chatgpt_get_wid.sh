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

echo "VERIFY_CHATGPT_GET_WID_OK"
