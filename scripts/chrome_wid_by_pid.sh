#!/usr/bin/env bash
set -euo pipefail

PID="${1:-}"
if [ -z "$PID" ]; then
  echo "ERROR_NO_PID" >&2
  exit 3
fi

declare -a cand_pids=()
cand_pids+=("$PID")
for p in "${cand_pids[@]}"; do
  while read -r child; do
    [ -n "$child" ] && cand_pids+=("$child")
  done < <(pgrep -P "$p" 2>/dev/null || true)
done

declare -a wids=()
for p in "${cand_pids[@]}"; do
  while read -r wid; do
    [ -n "$wid" ] && wids+=("$wid")
  done < <(wmctrl -lp 2>/dev/null | awk -v pid="$p" '$3==pid {print $1}')
done

if [ "${#wids[@]}" -eq 0 ]; then
  mapfile -t wids < <(xdotool search --pid "$PID" 2>/dev/null || true)
fi
if [ "${#wids[@]}" -eq 0 ]; then
  echo "ERROR_NO_WID pid=$PID" >&2
  exit 3
fi

if [ "${#wids[@]}" -gt 1 ]; then
  echo "MULTI_WIDS pid=$PID count=${#wids[@]}" >&2
  for wid in "${wids[@]}"; do
    title="$(xdotool getwindowname "$wid" 2>/dev/null || true)"
    printf 'WID_DEC=%s TITLE=%s\n' "$wid" "$title" >&2
  done
fi

wid_dec="${wids[-1]}"
wid_hex="$(printf '0x%08x' "$wid_dec")"

echo "WID_HEX=$wid_hex"
