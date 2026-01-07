#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="$(mktemp)"

: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT

cleanup() {
  if [[ -n "${service_pid:-}" ]]; then
    kill "${service_pid}" 2>/dev/null || true
    wait "${service_pid}" 2>/dev/null || true
  fi
  rm -f "${LOG_FILE}"
}
trap cleanup EXIT

mkdir -p "${ROOT}/diagnostics/chatgpt_queue/inbox"
mkdir -p "${ROOT}/diagnostics/chatgpt_queue/outbox"
mkdir -p "${ROOT}/diagnostics/chatgpt_queue/logs"
mkdir -p "${ROOT}/diagnostics/chatgpt_queue/processed"

cd "${ROOT}"

( timeout 300s python3 -m lucy_agents.chatgpt_service >"${LOG_FILE}" 2>&1 ) &
service_pid=$!

ready=0
for _ in $(seq 1 50); do
  if grep -q "SERVICE_READY" "${LOG_FILE}"; then
    ready=1
    break
  fi
  sleep 0.2
 done

if [[ "${ready}" -ne 1 ]]; then
  echo "ERROR: service did not start" >&2
  tail -n 80 "${LOG_FILE}" >&2 || true
  exit 1
fi

out="$(./scripts/chatgpt_service_ask.sh "Respondé exactamente con: OK")"
if [[ "${out}" != "OK" ]]; then
  echo "ERROR: unexpected answer: '${out}'" >&2
  tail -n 80 "${LOG_FILE}" >&2 || true
  exit 1
fi

echo "VERIFY_CHATGPT_SERVICE_OK"
