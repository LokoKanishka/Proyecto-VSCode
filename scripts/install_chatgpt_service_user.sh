#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
UNIT_SRC="${ROOT}/systemd/lucy-chatgpt-service.service"
UNIT_DIR="${HOME}/.config/systemd/user"
UNIT_DST="${UNIT_DIR}/lucy-chatgpt-service.service"

if [[ ! -f "${UNIT_SRC}" ]]; then
  echo "ERROR: missing unit file: ${UNIT_SRC}" >&2
  exit 1
fi

mkdir -p "${UNIT_DIR}"
cp -f "${UNIT_SRC}" "${UNIT_DST}"

systemctl --user daemon-reload
systemctl --user enable --now lucy-chatgpt-service.service

enabled="$(systemctl --user is-enabled lucy-chatgpt-service.service || true)"
active="$(systemctl --user is-active lucy-chatgpt-service.service || true)"

if [[ "${enabled}" != "enabled" ]]; then
  echo "ERROR: service not enabled (state=${enabled})" >&2
  exit 1
fi
if [[ "${active}" != "active" ]]; then
  echo "ERROR: service not active (state=${active})" >&2
  exit 1
fi

echo "SERVICE_ENABLED=1"
echo "SERVICE_ACTIVE=1"
