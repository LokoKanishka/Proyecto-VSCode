#!/usr/bin/env bash
set -euo pipefail

systemctl --user stop lucy-chatgpt-service.service || true
systemctl --user disable lucy-chatgpt-service.service || true

echo "SERVICE_DISABLED=1"
