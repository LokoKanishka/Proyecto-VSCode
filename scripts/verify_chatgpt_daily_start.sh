#!/usr/bin/env bash
set -euo pipefail

LUCY_CHATGPT_DAILY_ENABLE_SERVICE=1 ./scripts/chatgpt_daily_start.sh | tee /tmp/chatgpt_daily_start.log

grep -q "CHATGPT_DAILY_START_OK" /tmp/chatgpt_daily_start.log

echo "VERIFY_CHATGPT_DAILY_START_OK"
