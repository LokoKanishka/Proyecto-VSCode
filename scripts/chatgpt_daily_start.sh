#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [[ -f "$ROOT/scripts/chatgpt_profile_free_env.sh" ]]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/chatgpt_profile_free_env.sh"
fi

export CHATGPT_WID_PIN_ONLY=1
"${ROOT}/scripts/chatgpt_preflight.sh"

if [[ "${LUCY_CHATGPT_DAILY_ENABLE_SERVICE:-0}" -eq 1 ]]; then
  "${ROOT}/scripts/chatgpt_service_enable.sh"
fi

service_active=0
if command -v systemctl >/dev/null 2>&1; then
  if systemctl --user is-active --quiet lucy-chatgpt-service.service; then
    service_active=1
  fi
fi

if [[ "${service_active}" -eq 1 ]]; then
  out="$(python3 -m lucy_agents.chatgpt_client "Respondé exactamente con: OK")"
else
  out="$(python3 -m lucy_agents.chatgpt_bridge "Respondé exactamente con: OK")"
fi

if [[ "${out}" != "OK" ]]; then
  echo "ERROR: unexpected answer: '${out}'" >&2
  exit 1
fi

echo "CHATGPT_DAILY_START_OK"
