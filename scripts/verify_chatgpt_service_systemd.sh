#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT}"

./scripts/install_chatgpt_service_user.sh

active=0
for _ in $(seq 1 20); do
  if systemctl --user is-active --quiet lucy-chatgpt-service.service; then
    active=1
    break
  fi
  sleep 0.5
 done

if [[ "${active}" -ne 1 ]]; then
  echo "ERROR: service not active" >&2
  systemctl --user status lucy-chatgpt-service.service >&2 || true
  exit 1
fi

out="$(python3 -m lucy_agents.chatgpt_client "Respondé exactamente con: OK")"
if [[ "${out}" != "OK" ]]; then
  echo "ERROR: unexpected answer: '${out}'" >&2
  exit 1
fi

systemctl --user stop lucy-chatgpt-service.service

if systemctl --user is-active --quiet lucy-chatgpt-service.service; then
  echo "ERROR: service still active after stop" >&2
  systemctl --user status lucy-chatgpt-service.service >&2 || true
  exit 1
fi

echo "VERIFY_CHATGPT_SERVICE_SYSTEMD_OK"
