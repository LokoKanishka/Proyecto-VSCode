#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

# 1) override explícito
if [ -n "${CHATGPT_WID_HEX:-}" ]; then
  echo "$CHATGPT_WID_HEX"
  exit 0
fi

# Helper: buscar en wmctrl por regex (título) y devolver WID
_find_by_title() {
  local pat="$1"
  wmctrl -l | awk -v pat="$pat" 'BEGIN{IGNORECASE=1} $0 ~ pat {print $1; exit}'
}

# 2) Prioridad: ventana cuyo título sea LUCY_REQ_... - Google Chrome
WID="$(_find_by_title "LUCY_REQ_[0-9]+_[0-9]+.*- Google Chrome$")"
if [ -n "${WID:-}" ]; then
  echo "$WID"
  exit 0
fi

# 3) Ventana que diga ChatGPT - Google Chrome
WID="$(_find_by_title "ChatGPT.*- Google Chrome$")"
if [ -n "${WID:-}" ]; then
  echo "$WID"
  exit 0
fi

# 4) Cualquier ventana con "chatgpt" en el título (por si no termina con - Google Chrome)
WID="$(_find_by_title "chatgpt")"
if [ -n "${WID:-}" ]; then
  echo "$WID"
  exit 0
fi

echo "ERROR: no pude detectar la ventana de ChatGPT en Chrome." >&2
echo "CAND (chrome):" >&2
wmctrl -l | awk 'BEGIN{IGNORECASE=1} /- Google Chrome$/ {print " -", $0}' >&2 || true
exit 2
