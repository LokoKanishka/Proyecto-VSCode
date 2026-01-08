#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"

CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
if [[ "${CHATGPT_TARGET}" != "paid" ]]; then
  echo "ERROR: chatgpt_paid_get_url requiere CHATGPT_TARGET=paid" >&2
  exit 2
fi

WID_HEX="${1:-${CHATGPT_WID_HEX:-}}"
if [[ -z "${WID_HEX:-}" ]]; then
  WID_HEX="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR: no pude resolver WID para paid_get_url" >&2
  exit 3
fi

out="$("$HOST_EXEC" "bash -lc '
set -euo pipefail
WID_HEX=\"${WID_HEX}\"
WID_DEC=\$(printf \"%d\" \"\$WID_HEX\")

wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true
xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true
sleep 0.12

xdotool key --window \"\$WID_DEC\" ctrl+l 2>/dev/null || true
sleep 0.05
xdotool key --window \"\$WID_DEC\" ctrl+c 2>/dev/null || true
sleep 0.12

read_clip() {
  local t=\"\"
  t=\$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true)
  if [[ -n \"\$t\" ]]; then
    printf \"%s\" \"\$t\"
    return 0
  fi
  t=\$(timeout 2s xsel --clipboard --output 2>/dev/null || true)
  printf \"%s\" \"\$t\"
}

url=\"\"
for _ in \$(seq 1 10); do
  url=\"\$(read_clip)\"
  [[ -n \"\$url\" ]] && break
  sleep 0.08
done
printf \"%s\" \"\$url\"
'")"

url="$(printf '%s' "$out" | tr -d '\r')"
if [[ -z "${url:-}" ]]; then
  echo "ERROR: URL vacia" >&2
  exit 4
fi
if [[ "${url}" != http*://* ]]; then
  echo "ERROR: URL invalida: ${url}" >&2
  exit 4
fi

printf '%s\n' "$url"
