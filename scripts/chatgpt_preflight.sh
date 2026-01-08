#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export CHATGPT_TARGET="${CHATGPT_TARGET:-free}"
TARGET="${CHATGPT_TARGET:-paid}"
PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin_${TARGET}}"

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
  if systemctl --user cat "${SERVICE}" >/dev/null 2>&1; then
    echo "SERVICE_INSTALLED=1"
    service_installed=1
  else
    echo "SERVICE_INSTALLED=0"
    service_installed=0
  fi
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
  if [[ "${LUCY_CHATGPT_SERVICE_AUTOSTART:-0}" -eq 1 ]]; then
    echo "SERVICE_AUTOSTART=1"
    if [[ "${service_installed:-0}" -eq 1 ]] && ! systemctl --user is-active --quiet "${SERVICE}"; then
      if systemctl --user start "${SERVICE}"; then
        if systemctl --user is-active --quiet "${SERVICE}"; then
          echo "SERVICE_AUTOSTART_RESULT=started"
        else
          echo "SERVICE_AUTOSTART_RESULT=failed"
        fi
      else
        echo "SERVICE_AUTOSTART_RESULT=failed"
      fi
    else
      echo "SERVICE_AUTOSTART_RESULT=noop"
    fi
  fi
else
  echo "SYSTEMCTL_MISSING=1"
fi

echo "CHATGPT_PREFLIGHT_OK"
