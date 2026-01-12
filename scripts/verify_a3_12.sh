#!/usr/bin/env bash
set -euo pipefail
: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

source "$ROOT/scripts/_verify_common.sh"

ASK="$ROOT/scripts/chatgpt_ui_ask_x11.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
DISP="$ROOT/lucy_agents/x11_dispatcher.py"
COPY="$ROOT/scripts/chatgpt_copy_chat_text.sh"

command -v timeout >/dev/null 2>&1 || { echo "ERROR: falta 'timeout' (coreutils)" >&2; exit 2; }

# “env frío” a propósito
unset CHATGPT_WID_HEX || true

TIMEOUT_SEC="${A3_12_TIMEOUT_SEC:-${A3_12_TIMEOUT:-260}}"

echo "== A3.12 verify (timeout=${TIMEOUT_SEC}s) =="

WID="$("$GET_WID" 2>/tmp/a3_12_get_wid.err || true)"
echo "WID=$WID"
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: get_wid devolvió vacío" >&2
  echo "--- get_wid stderr ---" >&2
  sed -n '1,200p' /tmp/a3_12_get_wid.err >&2 || true
  echo "--- wmctrl host (grep chatgpt) ---" >&2
  "$HOST_EXEC" 'wmctrl -lx | grep -i chatgpt || true' >&2 || true
  exit 3
fi
export CHATGPT_WID_HEX="$WID"

# ejecutar ask con timeout
set +e
timeout "${TIMEOUT_SEC}s" "$ASK" "Respondé exactamente con: OK" \
  > /tmp/a3_12_ans.txt 2> /tmp/a3_12_err.txt
RC=$?
set -e

ANS="$(cat /tmp/a3_12_ans.txt 2>/dev/null || true)"

if [[ "$RC" -eq 0 ]] && echo "$ANS" | grep -qE '^LUCY_ANSWER_[0-9]+_[0-9]+: OK$'; then
  echo "VERIFY_A3_12_OK: $ANS"
  exit 0
fi

echo "ERROR: A3.12 FAIL" >&2
echo "RC=$RC" >&2
echo "ANS='$ANS'" >&2
echo "--- ask stderr ---" >&2
sed -n '1,240p' /tmp/a3_12_err.txt >&2 || true

echo >&2
echo "--- wmctrl host (grep chatgpt) ---" >&2
"$HOST_EXEC" 'wmctrl -lx | grep -i chatgpt || true' >&2 || true

echo >&2
echo "--- screenshot WID (post-fail) ---" >&2
set +e
python3 -u "$DISP" screenshot "$WID" > /tmp/a3_12_fail_shot_out.txt 2>/tmp/a3_12_fail_shot_err.txt
set -e
cat /tmp/a3_12_fail_shot_out.txt >&2 || true
cat /tmp/a3_12_fail_shot_err.txt >&2 || true

P="$(sed -n 's/^PATH[[:space:]]\+\([^[:space:]]\+\).*/\1/p' /tmp/a3_12_fail_shot_out.txt | head -n 1)"
if [[ -n "${P:-}" ]]; then
  echo "FAIL_SHOT_PATH=$P" >&2
  ls -la "$P" >&2 || true
fi

echo >&2
echo "--- COPY tail (post-fail) ---" >&2
set +e
timeout 25s "$COPY" > /tmp/a3_12_fail_chat.txt 2>/tmp/a3_12_fail_copy_err.txt
set -e
echo "COPY_BYTES=$(wc -c < /tmp/a3_12_fail_chat.txt 2>/dev/null || echo 0)" >&2
tail -n 80 /tmp/a3_12_fail_chat.txt >&2 || true
echo "--- copy stderr ---" >&2
tail -n 120 /tmp/a3_12_fail_copy_err.txt >&2 || true

exit 1
