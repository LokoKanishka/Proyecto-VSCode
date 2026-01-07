#!/usr/bin/env bash
set -euo pipefail

./scripts/chatgpt_preflight.sh | tee /tmp/chatgpt_preflight.log

grep -q "CHATGPT_PREFLIGHT_OK" /tmp/chatgpt_preflight.log

echo "VERIFY_CHATGPT_PREFLIGHT_OK"
