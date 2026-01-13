#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
WATCHER="$ROOT/scripts/ui_dialog_watch.sh"
FIXTURE="$ROOT/tests/fixtures/modal_test.html"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

echo "== UI DIALOG SMOKE TEST =="

# 1. Open Chrome
echo "Opening Chrome with fixture..."
# Try x11_host_exec to run chrome on host? 
# Or local? If display is forwarded, local is fine.
# But ui_dialog_watch checks HOST windows.
# If I run chrome here, it must show on host X server.
# Assuming 'google-chrome' is available or checks path.

url="file://$FIXTURE"
cmd="google-chrome --new-window \"$url\" >/dev/null 2>&1 &"

# Try running strictly via host exec to ensure it appears on the same X session we probe
"$HOST_EXEC" "nohup google-chrome --new-window \"$url\" >/dev/null 2>&1 &" || true
# Fallback local
nohup google-chrome --new-window "$url" >/dev/null 2>&1 &

sleep 4

# 2. Run Watcher for 5 seconds
echo "Running watcher..."
out=$(mktemp)
err=$(mktemp)

# Run watcher for 8s
timeout 10s "$WATCHER" --for 8 >"$out" 2>"$err" || true

# 3. Check logs
echo "--- WATCHER LOGS ---"
cat "$err"
echo "--------------------"

if grep -q "__LUCY_UI_DIALOG__.*HIT=1" "$err"; then
  echo "SUCCESS: Dialog rule hit."
  rm -f "$out" "$err"
  exit 0
else
  echo "FAIL: No dialog hit detected."
  rm -f "$out" "$err"
  exit 1
fi
