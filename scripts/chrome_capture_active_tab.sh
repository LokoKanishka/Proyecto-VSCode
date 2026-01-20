#!/usr/bin/env bash
set -euo pipefail

WID_HEX="${1:-}"
OUTDIR="${2:-}"

if [ -z "${WID_HEX:-}" ] || [ -z "${OUTDIR:-}" ]; then
  echo "USAGE: chrome_capture_active_tab.sh <WID_HEX> <outdir>" >&2
  exit 2
fi

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR_MISSING_TOOL: $1" >&2; exit 3; }; }
need xprop

mkdir -p "$OUTDIR"
printf '%s\n' "$WID_HEX" >"$OUTDIR/wid_hex.txt"

# WID must be live
set +e
xprop -id "$WID_HEX" _NET_WM_NAME >/dev/null 2>&1
live_rc=$?
set -e
if [ "$live_rc" -ne 0 ]; then
  echo "ERROR_BADWINDOW: $WID_HEX" >&2
  exit 3
fi

# Title
title="$(xprop -id "$WID_HEX" _NET_WM_NAME 2>/dev/null | sed -n 's/.*= "\(.*\)".*/\1/p' | head -n 1 || true)"
printf '%s\n' "${title:-}" >"$OUTDIR/title.txt"

# URL: prefer omnibox capture (robusto)
OMNI="$ROOT/scripts/chrome_capture_url_omnibox.sh"
if [ -x "$OMNI" ]; then
  # Esto escribe url.txt/title.txt/ok.txt dentro de OUTDIR
  set +e
  "$OMNI" "$WID_HEX" "$OUTDIR" >/dev/null 2>&1
  set -e
fi

# Si por cualquier razón sigue vacío, dejamos archivo igual (pero no debería pasar ya)
: > /dev/null

# Print in machine-friendly form for callers
url=""
if [ -r "$OUTDIR/url.txt" ]; then
  url="$(head -n 1 "$OUTDIR/url.txt" | tr -d '\r' || true)"
fi
printf 'TITLE=%s\n' "${title:-}"
printf 'URL=%s\n' "${url:-}"

exit 0
