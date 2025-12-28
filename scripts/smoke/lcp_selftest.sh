#!/usr/bin/env bash
set -euo pipefail

pass=0
fail=0

sanitize() {
  # Remove CR and control chars (includes DEL 0x7f)
  tr -d '\r' | LC_ALL=C tr -d '\000-\010\013\014\016-\037\177'
}

extract_answer() {
  local tok="$1" file="$2"
  sanitize <"$file" | grep -E "^LUCY_ANSWER_${tok}:" | tail -n 1 || true
}

assert_eq() {
  local name="$1" got="$2" exp="$3"
  if [[ "$got" == "$exp" ]]; then
    echo "PASS: $name"
    pass=$((pass+1))
  else
    echo "FAIL: $name"
    echo "  got: $got"
    echo "  exp: $exp"
    fail=$((fail+1))
  fi
}

tmpdir="$(mktemp -d)"
trap 'rm -rf "$tmpdir"' EXIT

# Case 1: DEL prefix at line start
TOK="1766900000_11111"
f="$tmpdir/case1.txt"
TOK="$TOK" python3 - <<'PY' >"$f"
import os
DEL = chr(127)
tok = os.environ["TOK"]
print("Omitir e ir al contenido")
print(f"{DEL}LUCY_REQ_{tok}: Responde exactamente con: OK")
print("Debe empezar EXACTAMENTE con: LUCY_ANSWER_%s: (dos puntos y un espacio)" % tok)
print("ChatGPT Plus")
print(f"{DEL}LUCY_ANSWER_{tok}: OK")
PY
got="$(extract_answer "$TOK" "$f")"
assert_eq "case1_del_prefix" "$got" "LUCY_ANSWER_${TOK}: OK"

# Case 2: avoid false positive on instruction line
TOK="1766900000_22222"
f="$tmpdir/case2.txt"
cat >"$f" <<EOF
LUCY_REQ_${TOK}: Responde exactamente con: OK

Responde SOLO con UNA linea.
Debe empezar EXACTAMENTE con: LUCY_ANSWER_${TOK}: (dos puntos y un espacio)
y en ESA MISMA LINEA, despues de eso, pone tu respuesta.
ChatGPT Plus
LUCY_ANSWER_${TOK}: OK
EOF
got="$(extract_answer "$TOK" "$f")"
assert_eq "case2_no_false_positive" "$got" "LUCY_ANSWER_${TOK}: OK"

# Case 3: multiple tokens, pick the correct one
TOK_A="1766900000_33333"
TOK_B="1766900000_44444"
f="$tmpdir/case3.txt"
cat >"$f" <<EOF
LUCY_ANSWER_${TOK_A}: NO
LUCY_ANSWER_${TOK_B}: OK
EOF
got="$(extract_answer "$TOK_B" "$f")"
assert_eq "case3_pick_correct_token" "$got" "LUCY_ANSWER_${TOK_B}: OK"

# Case 4: CRLF mixed in
TOK="1766900000_55555"
f="$tmpdir/case4.txt"
TOK="$TOK" python3 - <<'PY' >"$f"
import os
tok = os.environ["TOK"]
s = "LUCY_ANSWER_%s: OK\r\n" % tok
print("x\r")
print(s, end="")
PY
got="$(extract_answer "$TOK" "$f")"
assert_eq "case4_strip_cr" "$got" "LUCY_ANSWER_${TOK}: OK"

echo
echo "LCP_SELFTEST: pass=$pass fail=$fail"
if [[ "$fail" -ne 0 ]]; then
  exit 1
fi
