#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# --- LUCY_PIN_LIVE_GUARD_ENTRY: ensure diego pin points to a live WID (avoid BadWindow) ---
PIN_FILE_DEFAULT="$ROOT/diagnostics/pins/chrome_diego.wid"
PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$PIN_FILE_DEFAULT}"
ENSURE_LIVE="$ROOT/scripts/chrome_diego_pin_ensure_live.sh"
if [ ! -x "$ENSURE_LIVE" ]; then
  echo "ERROR_NO_PIN_ENSURE: $ENSURE_LIVE" >&2
  exit 3
fi
CHROME_DIEGO_PIN_FILE="$PIN_FILE" "$ENSURE_LIVE" "https://chatgpt.com/" >/dev/null
# --- /LUCY_PIN_LIVE_GUARD_ENTRY ---

export CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
export CHATGPT_WID_PIN_FILE="${CHATGPT_WID_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"
export CHATGPT_WID_PIN_FILE_PAID="${CHATGPT_WID_PIN_FILE_PAID:-$ROOT/diagnostics/pins/chrome_diego.wid}"
export CHATGPT_PAID_TEST_THREAD_FILE="${CHATGPT_PAID_TEST_THREAD_FILE:-$ROOT/diagnostics/chatgpt/paid_test_thread.url}"

# --- A24_DIEGO_CLIENT_GATE (cliente Chrome, no sitio) ---
# Exige que el cliente sea el perfil Diego (email gate) y fija el WID base desde diagnostics/pins/chrome_diego.wid.
CHROME_PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
CHROME_DIEGO_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"
CHROME_DIEGO_PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"
export CHROME_PROFILE_NAME CHROME_DIEGO_EMAIL CHROME_DIEGO_PIN_FILE

if [ -x "$ROOT/scripts/chrome_guard_diego_client.sh" ]; then
  gate_out="$("$ROOT/scripts/chrome_guard_diego_client.sh" "https://www.google.com/" 2>/dev/null || true)"
  gate_wid="$(printf '%s\n' "$gate_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
  gate_email="$(printf '%s\n' "$gate_out" | awk -F= '/^EMAIL=/{print $2}' | tail -n 1)"
  if [ -z "${gate_wid:-}" ]; then
    echo "ERROR_DIEGO_GATE_NO_WID (chrome_guard_diego_client.sh)" >&2
    exit 3
  fi
  if [ -z "${gate_email:-}" ] || [ "$gate_email" != "$CHROME_DIEGO_EMAIL" ]; then
    echo "ERROR_DIEGO_GATE_EMAIL expected=$CHROME_DIEGO_EMAIL got=$gate_email" >&2
    exit 3
  fi

  # Este es EL WID autorizado para interactuar (cliente Diego)
  export CHROME_WID_HEX="$gate_wid"
  export CHATGPT_WID_HEX="$gate_wid"

  # Pin único: todo ChatGPT usa el pin del cliente Diego (no ACTIVE_WINDOW)
  export CHATGPT_WID_PIN_FILE="$CHROME_DIEGO_PIN_FILE"
  export CHATGPT_ALLOW_ACTIVE_WINDOW=0
  export CHATGPT_WID_PIN_ONLY=1
fi
# --- end A24_DIEGO_CLIENT_GATE ---
