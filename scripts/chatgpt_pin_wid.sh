#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin}"
TITLE_INCLUDE="${CHATGPT_TITLE_INCLUDE:-ChatGPT}"
TITLE_EXCLUDE="${CHATGPT_TITLE_EXCLUDE:-V.S.Code}"

get_active_wid() {
  local raw
  raw="$("$HOST_EXEC" 'xprop -root _NET_ACTIVE_WINDOW' 2>/dev/null \
    | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1)"
  if [[ -n "${raw:-}" ]]; then
    printf '0x%08x\n' "$((raw))"
  fi
}

get_title() {
  local wid="$1"
  local wins
  wins="$("$HOST_EXEC" 'wmctrl -l' 2>/dev/null || true)"
  awk -v w="$wid" '$1==w { $1=""; $2=""; $3=""; sub(/^ +/, ""); print; exit }' <<< "$wins"
}

wid="$(get_active_wid)"
if [[ -z "${wid:-}" ]]; then
  echo "ERROR: no active window detected" >&2
  exit 1
fi

title="$(get_title "$wid")"
if [[ -n "${TITLE_INCLUDE}" ]] && [[ "${title}" != *"${TITLE_INCLUDE}"* ]]; then
  echo "ERROR: active window is not ChatGPT (TITLE='${title}')" >&2
  exit 1
fi
if [[ -n "${TITLE_EXCLUDE}" ]] && [[ "${title}" == *"${TITLE_EXCLUDE}"* ]]; then
  echo "ERROR: active window is excluded (TITLE='${title}')" >&2
  exit 1
fi

mkdir -p "$(dirname "$PIN_FILE")"
{
  echo "$wid"
  echo "TITLE=$title"
} > "$PIN_FILE"

printf 'PINNED_WID=%s\n' "$wid"
printf 'PIN_FILE=%s TITLE=%s\n' "$PIN_FILE" "$title" >&2
