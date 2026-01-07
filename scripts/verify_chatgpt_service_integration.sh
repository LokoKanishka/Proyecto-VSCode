#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_LOG="/tmp/chatgpt_service.bg.log"

cleanup() {
  if [[ -n "${service_pid:-}" ]]; then
    kill "${service_pid}" 2>/dev/null || true
    wait "${service_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

run_flow() {
  local label="$1"
  local expect_path="$2"
  shift 2
  local out_file
  local err_file
  out_file="$(mktemp)"
  err_file="$(mktemp)"

  "$@" >"${out_file}" 2>"${err_file}"

  if ! grep -xq "OK" "${out_file}"; then
    echo "ERROR: ${label} missing OK" >&2
    cat "${out_file}" >&2
    cat "${err_file}" >&2
    rm -f "${out_file}" "${err_file}"
    exit 1
  fi

  if ! grep -q "${expect_path}" "${out_file}" "${err_file}"; then
    echo "ERROR: ${label} missing ${expect_path}" >&2
    cat "${out_file}" >&2
    cat "${err_file}" >&2
    rm -f "${out_file}" "${err_file}"
    exit 1
  fi

  cat "${out_file}"
  cat "${err_file}" >&2
  rm -f "${out_file}" "${err_file}"
}

cd "${ROOT}"

# Case A: service running
rm -f "${SERVICE_LOG}" 2>/dev/null || true
./scripts/chatgpt_service_run.sh >"${SERVICE_LOG}" 2>&1 &
service_pid=$!

ready=0
for _ in $(seq 1 50); do
  if grep -q "SERVICE_READY" "${SERVICE_LOG}"; then
    ready=1
    break
  fi
  sleep 0.2
 done

if [[ "${ready}" -ne 1 ]]; then
  echo "ERROR: service did not start" >&2
  tail -n 120 "${SERVICE_LOG}" >&2 || true
  exit 1
fi

run_flow "SERVICE" "CHATGPT_PATH=SERVICE" \
  env LUCY_CHATGPT_USE_SERVICE=1 LUCY_CHATGPT_SERVICE_TIMEOUT_SEC=220 \
  python3 - <<'PY'
import sys
from lucy_agents.voice_actions import maybe_handle_desktop_intent

text = "preguntale a chatgpt: Respondé exactamente con: OK"
result = maybe_handle_desktop_intent(text)
if not isinstance(result, tuple) or len(result) != 2:
    print(f"ERROR: unexpected result: {result!r}", file=sys.stderr)
    sys.exit(1)
handled, answer = result
if not handled:
    print("ERROR: chatgpt request not handled", file=sys.stderr)
    sys.exit(1)
print((answer or "").strip())
PY

kill "${service_pid}" 2>/dev/null || true
wait "${service_pid}" 2>/dev/null || true
service_pid=""

# Case B: fallback when service is down
run_flow "FALLBACK" "CHATGPT_PATH=DIRECT_FALLBACK" \
  env LUCY_CHATGPT_USE_SERVICE=1 LUCY_CHATGPT_SERVICE_TIMEOUT_SEC=6 \
  python3 - <<'PY'
import sys
from lucy_agents.voice_actions import maybe_handle_desktop_intent

text = "preguntale a chatgpt: Respondé exactamente con: OK"
result = maybe_handle_desktop_intent(text)
if not isinstance(result, tuple) or len(result) != 2:
    print(f"ERROR: unexpected result: {result!r}", file=sys.stderr)
    sys.exit(1)
handled, answer = result
if not handled:
    print("ERROR: chatgpt request not handled", file=sys.stderr)
    sys.exit(1)
print((answer or "").strip())
PY

echo "VERIFY_CHATGPT_SERVICE_INTEGRATION_OK"
