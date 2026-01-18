#!/usr/bin/env bash
set -euo pipefail

WID_HEX="${1:-}"
if [ -z "${WID_HEX:-}" ]; then
  echo "USAGE: chrome_wid_profile_dir.sh <WID_HEX>" >&2
  exit 2
fi

pid="$(xprop -id "$WID_HEX" _NET_WM_PID 2>/dev/null | awk -F'= ' '{print $2}' | tr -d ' ')"
if [ -z "${pid:-}" ]; then
  exit 3
fi

cmdline="$(tr '\0' ' ' </proc/"$pid"/cmdline 2>/dev/null || true)"
if [ -z "${cmdline:-}" ]; then
  exit 3
fi

profile_dir=""
user_data_dir=""

profile_dir="$(printf '%s\n' "$cmdline" | sed -n 's/.*--profile-directory=\([^ ]*\).*/\1/p' | head -n 1)"
user_data_dir="$(printf '%s\n' "$cmdline" | sed -n 's/.*--user-data-dir=\([^ ]*\).*/\1/p' | head -n 1)"

if [ -n "${profile_dir:-}" ]; then
  echo "PROFILE_DIR=$profile_dir"
fi
if [ -n "${user_data_dir:-}" ]; then
  echo "USER_DATA_DIR=$user_data_dir"
fi

if [ -z "${profile_dir:-}" ]; then
  echo "PROFILE_DIR=Default"
fi
