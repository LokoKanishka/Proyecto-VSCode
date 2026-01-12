#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
DISPATCHER="$ROOT/lucy_agents/x11_dispatcher.py"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"

FILE="${1:-}"
if [ -z "${FILE}" ] || [ ! -f "${FILE}" ]; then
  echo "USO: $0 <archivo>" >&2
  exit 2
fi

WID="${CHATGPT_WID_HEX:-}"
if [ -z "${WID}" ] && [ -x "${GET_WID}" ]; then
  WID="$("${GET_WID}" 2>/dev/null || true)"
fi
if [ -z "${WID}" ]; then
  echo "ERROR: no hay WID (CHATGPT_WID_HEX ni chatgpt_get_wid.sh)" >&2
  exit 2
fi

TEXT="$(cat "${FILE}")"

FOCUS_OUT="$(python3 -u "${DISPATCHER}" focus_window "${WID}" 2>&1 || true)"
if printf '%s\n' "${FOCUS_OUT}" | head -n 1 | grep -q '^ERR '; then
  echo "ERROR focus_window: ${FOCUS_OUT}" >&2
  exit 1
fi

TYPE_OUT="$(python3 -u "${DISPATCHER}" type_text "${WID}" "${TEXT}" 2>&1 || true)"
if printf '%s\n' "${TYPE_OUT}" | head -n 1 | grep -q '^ERR '; then
  echo "ERROR type_text: ${TYPE_OUT}" >&2
  exit 1
fi

if [ "${CHATGPT_POST_SEND:-0}" = "1" ]; then
  SEND_KEY="${CHATGPT_POST_SEND_KEY:-Return}"
  SEND_OUT="$(python3 -u "${DISPATCHER}" send_keys "${WID}" "${SEND_KEY}" 2>&1 || true)"
  if printf '%s\n' "${SEND_OUT}" | head -n 1 | grep -q '^ERR '; then
    echo "ERROR send_keys: ${SEND_OUT}" >&2
    exit 1
  fi
fi

echo "POST_OK"
