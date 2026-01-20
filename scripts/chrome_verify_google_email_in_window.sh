\
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -r "$ROOT/scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/x11_env.sh"
fi

WID_HEX="${1:-}"
EXPECT_EMAIL="${2:-}"
MAX_SECONDS="${3:-12}"

if [ -z "${WID_HEX:-}" ] || [ -z "${EXPECT_EMAIL:-}" ]; then
  echo "USAGE: chrome_verify_google_email_in_window.sh <WID_HEX> <expect_email> [max_seconds]" >&2
  exit 2
fi

need() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR_MISSING_TOOL: $1" >&2; exit 3; }; }
need wmctrl
need xdotool

CLIP_READ=""
if command -v xclip >/dev/null 2>&1; then
  CLIP_READ='xclip -o -selection clipboard'
elif command -v xsel >/dev/null 2>&1; then
  CLIP_READ='xsel --clipboard --output'
else
  echo "ERROR_NO_CLIP_TOOL: install xclip (recommended) or xsel" >&2
  exit 3
fi

ENSURE="$ROOT/scripts/chrome_ensure_url_in_window.sh"
if [ ! -x "$ENSURE" ]; then
  echo "ERROR_MISSING_ENSURE: $ENSURE" >&2
  exit 3
fi

OUTROOT="/tmp/lucy_verify_google_email"
OUT="$OUTROOT/$(date +%Y%m%d_%H%M%S)_$$"
mkdir -p "$OUT"

WID_DEC=$((WID_HEX))
wmctrl -ia "$WID_HEX" 2>/dev/null || true
xdotool windowactivate --sync "$WID_DEC" 2>/dev/null || true
sleep 0.12

# Página que suele listar cuentas con emails visibles (cliente Google)
TARGET="https://accounts.google.com/SignOutOptions"

set +e
"$ENSURE" "$WID_HEX" "$TARGET" "$MAX_SECONDS" >"$OUT/ensure.txt" 2>&1
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  echo "ERROR_ENSURE_SIGNOUTOPTIONS rc=$rc (see $OUT/ensure.txt)" >&2
  echo "OUTDIR=$OUT"
  exit 3
fi

# Intentar copiar texto de la página
xdotool key --window "$WID_DEC" --clearmodifiers Escape 2>/dev/null || true
sleep 0.05
xdotool key --window "$WID_DEC" --clearmodifiers ctrl+a 2>/dev/null || true
sleep 0.08
xdotool key --window "$WID_DEC" --clearmodifiers ctrl+c 2>/dev/null || true
sleep 0.18

set +e
txt="$(eval "$CLIP_READ" 2>/dev/null | tr -d '\r')"
set -e

printf '%s' "$txt" >"$OUT/clipboard.txt"

if printf '%s' "$txt" | grep -Fqi "$EXPECT_EMAIL"; then
  echo "OK_GOOGLE_EMAIL_IN_WINDOW"
  echo "WID_HEX=$WID_HEX"
  echo "EMAIL=$EXPECT_EMAIL"
  echo "OUTDIR=$OUT"
  exit 0
fi

echo "ERROR_EMAIL_NOT_FOUND (expected $EXPECT_EMAIL) (see $OUT/clipboard.txt)" >&2
echo "WID_HEX=$WID_HEX" >&2
echo "OUTDIR=$OUT" >&2
exit 3
