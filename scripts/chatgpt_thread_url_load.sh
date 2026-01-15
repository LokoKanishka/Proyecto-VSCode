#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
TARGET="${CHATGPT_TARGET:-free}"
PIN="$ROOT/diagnostics/chatgpt_thread_url_${TARGET}.txt"

if [[ -n "${CHATGPT_THREAD_URL:-}" ]]; then
  printf '%s\n' "$CHATGPT_THREAD_URL"
  exit 0
fi

if [[ -f "$PIN" ]]; then
  url="$(cat "$PIN" | tr -d '\r' | head -n 1)"
  if [[ -n "$url" ]]; then
    printf '%s\n' "$url"
    exit 0
  fi
fi

echo "ERROR_NO_THREAD_URL: faltó pin. Corré scripts/chatgpt_thread_url_set.sh estando en un /c/." >&2
exit 9
