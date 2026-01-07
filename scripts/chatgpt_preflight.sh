#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin}"

if [[ ! -f "${PIN_FILE}" ]]; then
  echo "ERROR: PIN_FILE_MISSING ${PIN_FILE}" >&2
  exit 2
fi

export CHATGPT_WID_PIN_ONLY=1
WID="$("${ROOT}/scripts/chatgpt_get_wid.sh")"
if [[ -z "${WID}" ]]; then
  echo "ERROR: PIN_INVALID" >&2
  exit 3
fi

echo "PIN_OK WID=${WID}"

SERVICE="lucy-chatgpt-service.service"
if command -v systemctl >/dev/null 2>&1; then
  if systemctl --user is-enabled --quiet "${SERVICE}"; then
    echo "SERVICE_ENABLED=1"
  else
    echo "SERVICE_ENABLED=0"
  fi
  if systemctl --user is-active --quiet "${SERVICE}"; then
    echo "SERVICE_ACTIVE=1"
  else
    echo "SERVICE_ACTIVE=0"
  fi
else
  echo "SYSTEMCTL_MISSING=1"
fi

echo "CHATGPT_PREFLIGHT_OK"
