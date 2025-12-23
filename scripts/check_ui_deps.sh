#!/usr/bin/env bash
set -euo pipefail

need=(xdotool wmctrl xclip)
missing=0

for bin in "${need[@]}"; do
  if command -v "$bin" >/dev/null 2>&1; then
    printf "OK: %s -> %s\n" "$bin" "$(command -v "$bin")"
  else
    printf "MISSING: %s\n" "$bin"
    missing=1
  fi
done

exit "$missing"
