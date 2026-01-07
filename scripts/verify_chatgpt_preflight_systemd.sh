#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT}"

./scripts/chatgpt_service_enable.sh

./scripts/chatgpt_preflight.sh

./scripts/chatgpt_service_disable.sh

./scripts/verify_a4_all.sh

echo "VERIFY_CHATGPT_PREFLIGHT_SYSTEMD_OK"
