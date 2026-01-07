#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

"${ROOT}/scripts/install_chatgpt_service_user.sh"

systemctl --user enable --now lucy-chatgpt-service.service

if ! systemctl --user is-enabled --quiet lucy-chatgpt-service.service; then
  echo "ERROR: service not enabled" >&2
  exit 1
fi
if ! systemctl --user is-active --quiet lucy-chatgpt-service.service; then
  echo "ERROR: service not active" >&2
  exit 1
fi

echo "SERVICE_ENABLED=1"
echo "SERVICE_ACTIVE=1"
