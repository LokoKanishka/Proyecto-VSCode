#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

: "${A3_12_STRESS_N:=10}"
: "${A3_12_STRESS_TIMEOUT_SEC:=180}"
: "${LUCY_CHATGPT_AUTO_CHAT:=1}"
export LUCY_CHATGPT_AUTO_CHAT

say() {
  echo "== $* =="
}

ASK="$ROOT/scripts/chatgpt_ui_ask_x11.sh"

for i in $(seq 1 "${A3_12_STRESS_N}"); do
  say "A3.12 STRESS ${i}/${A3_12_STRESS_N}"
  tmp_out="$(mktemp)"
  tmp_err="$(mktemp)"
  set +e
  CHATGPT_ASK_TIMEOUT_SEC="${A3_12_STRESS_TIMEOUT_SEC}" \
    "$ASK" "Respondé exactamente con: OK" >"$tmp_out" 2>"$tmp_err"
  rc=$?
  set -e

  ans="$(cat "$tmp_out" 2>/dev/null || true)"
  if [[ "$rc" -ne 0 ]] || ! printf '%s\n' "$ans" | grep -qE '^LUCY_ANSWER_[0-9]+_[0-9]+: OK$'; then
    echo "ERROR: A3.12 STRESS FAIL iter=${i}" >&2
    echo "RC=${rc}" >&2
    echo "ANS='${ans}'" >&2
    echo "--- ask stderr ---" >&2
    sed -n '1,240p' "$tmp_err" >&2 || true
    tmpdir="$(sed -n 's/^LUCY_ASK_TMPDIR=//p' "$tmp_err" | tail -n 1)"
    if [[ -n "${tmpdir:-}" ]]; then
      echo "FORENSICS_DIR=${tmpdir}" >&2
    fi
    rm -f "$tmp_out" "$tmp_err" 2>/dev/null || true
    exit 1
  fi

  rm -f "$tmp_out" "$tmp_err" 2>/dev/null || true
done

echo "VERIFY_A3_12_STRESS_OK"
