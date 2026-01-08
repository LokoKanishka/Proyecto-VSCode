#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

export CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-paid}"
export CHATGPT_WID_PIN_FILE="${CHATGPT_WID_PIN_FILE:-/tmp/lucy_chatgpt_wid_pin_paid}"
export CHATGPT_WID_PIN_FILE_PAID="${CHATGPT_WID_PIN_FILE_PAID:-/tmp/lucy_chatgpt_wid_pin_paid}"
export CHATGPT_PAID_TEST_THREAD_FILE="${CHATGPT_PAID_TEST_THREAD_FILE:-$ROOT/diagnostics/chatgpt/paid_test_thread.url}"
