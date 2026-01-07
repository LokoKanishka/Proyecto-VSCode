#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

mkdir -p "${ROOT}/diagnostics/chatgpt_queue/inbox"
mkdir -p "${ROOT}/diagnostics/chatgpt_queue/outbox"
mkdir -p "${ROOT}/diagnostics/chatgpt_queue/logs"
mkdir -p "${ROOT}/diagnostics/chatgpt_queue/processed"

cd "${ROOT}"
exec python3 -m lucy_agents.chatgpt_service
