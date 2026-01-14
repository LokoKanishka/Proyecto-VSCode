#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
export CHATGPT_TARGET="${CHATGPT_TARGET:-free}"

# Preflight: asegurar bridge X11 + ventana ChatGPT
"$ROOT/scripts/x11_file_agent_start.sh" >/dev/null 2>&1 || true
if [[ "${LUCY_AUTOSTART_CHATGPT:-1}" == "1" ]]; then
  "$ROOT/scripts/chatgpt_bridge_ensure.sh" >/dev/null 2>&1 || true
fi

# Resolver WID 1 sola vez (evita 10x ERROR_NO_WID)
WID_HEX="${CHATGPT_WID_HEX:-}"
if [[ -z "${WID_HEX:-}" ]]; then
  WID_HEX="$("$ROOT/scripts/chatgpt_get_wid.sh" 2>/dev/null || true)"
fi
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR_NO_WID: no hay ventana de ChatGPT detectable (target=${CHATGPT_TARGET})" >&2
  exit 4
fi
export CHATGPT_WID_HEX="$WID_HEX"
echo "__LUCY_COPY_META__ PRE_WID=${WID_HEX} TARGET=${CHATGPT_TARGET}" >&2

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPT="$ROOT/scripts/chatgpt_copy_messages_strict.sh"

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
START_AGENT="$ROOT/scripts/x11_file_agent_start.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"

# Preflight: intentar arrancar el bridge X11 (si aplica)
"$START_AGENT" >/dev/null 2>&1 || true

# Resolver WID una sola vez (evita 10x ERROR_NO_WID)
WID_HEX="${CHATGPT_WID_HEX:-}"
if [[ -z "${WID_HEX:-}" ]]; then
  WID_HEX="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID_HEX:-}" ]]; then
  if [[ "${LUCY_REQUIRE_CHATGPT_UI:-0}" == "1" ]]; then
    echo "FAIL: no se encontró ventana de ChatGPT (WID vacío)" >&2
    exit 4
  fi
  echo "SKIP: no se encontró ventana de ChatGPT (WID vacío). (LUCY_REQUIRE_CHATGPT_UI=1 para forzar FAIL)"
  exit 0
fi
export CHATGPT_WID_HEX="$WID_HEX"

echo "== RUNNING STRICT COPY VERIFICATION (10 iterations) =="

failures=0
successes=0

for i in $(seq 1 10); do
  printf "Iter %2d: " "$i"
  # Clean clipboard first to ensure we are getting fresh data (optional but good)
  # But the script overwrites it anyway.
  
  out=$(mktemp)
  if "$SCRIPT" > "$out"; then
    bytes=$(wc -c < "$out")
    if [[ "$bytes" -gt 200 ]]; then
      echo "OK ($bytes bytes)"
      successes=$((successes+1))
    else
      echo "FAIL (too small: $bytes bytes)"
      failures=$((failures+1))
    fi
  else
    echo "FAIL (script exit code)"
    failures=$((failures+1))
  fi
  rm -f "$out"
  sleep 1
done

echo "== RESULTS =="
echo "Success: $successes"
echo "Failure: $failures"

if [[ "$failures" -eq 0 ]]; then
  exit 0
else
  exit 1
fi
