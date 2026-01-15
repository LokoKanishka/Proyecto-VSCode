#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"

WID_HEX="${1:-${CHATGPT_WID_HEX:-}}"
if [[ -z "${WID_HEX:-}" ]]; then
  WID_HEX="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR: seteá CHATGPT_WID_HEX o pasalo como arg" >&2
  exit 3
fi

COPY_MODE="${LUCY_COPY_MODE:-auto}"
COPY_MESSAGES_ATTEMPTS="${LUCY_COPY_MESSAGES_ATTEMPTS:-3}"
COPY_INPUT_ATTEMPTS="${LUCY_COPY_INPUT_ATTEMPTS:-2}"
COPY_INPUT_PROBE="${LUCY_COPY_INPUT_PROBE:-0}"
ENSURE_FOCUS="$ROOT/scripts/chatgpt_ensure_input_focus.sh"
CLICK_MESSAGES="$ROOT/scripts/chatgpt_click_messages_zone.sh"

WID_DEC="$(printf "%d" "$WID_HEX" 2>/dev/null || echo 0)"
if [[ "${WID_DEC}" -le 0 ]]; then
  echo "ERROR: WID invalido: ${WID_HEX}" >&2
  exit 3
fi

geo="$("$HOST_EXEC" "xdotool getwindowgeometry --shell ${WID_DEC}" 2>/dev/null || true)"
eval "$geo" || true
: "${WIDTH:=1200}"
: "${HEIGHT:=900}"

bytes_len() {
  local t="$1"
  printf "%s" "$t" | wc -c | tr -d " \n"
}

copy_backoff() {
  case "$1" in
    1) printf '0.08' ;;
    2) printf '0.15' ;;
    *) printf '0.25' ;;
  esac
}

messages_click_params() {
  local attempt="$1"
  local y_pct=35
  case "$attempt" in
    2) y_pct=30 ;;
    3) y_pct=40 ;;
  esac
  local jitter=$(( (attempt - 1) * 4 ))
  printf '%s %s\n' "$y_pct" "$jitter"
}

copy_at() {
  local px="$1" py="$2"
  # Phase 4 (v6): Fix variable names (use local WID_HEX/DEC)
  local cmd="PX='${px}' PY='${py}' WID_HEX='${WID_HEX}' WID_DEC='${WID_DEC}'; "
  cmd+="set -euo pipefail; "
  cmd+="wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true; "
  cmd+="xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true; "
  cmd+="sleep 0.15; "
  cmd+="xdotool key --window "$WID_DEC" --clearmodifiers Escape 2>/dev/null || true; "
  cmd+="xdotool mousemove --window \"\$WID_DEC\" \"\$PX\" \"\$PY\" click 1 2>/dev/null || true; "
  cmd+="sleep 0.10; "
  cmd+="xdotool key --window "$WID_DEC" --clearmodifiers ctrl+a 2>/dev/null || true; "
  cmd+="sleep 0.10; "
  cmd+="xdotool key --window "$WID_DEC" --clearmodifiers ctrl+c 2>/dev/null || true; "
  cmd+="sleep 0.20; "
  cmd+="t=''; "
  cmd+="for i in \$(seq 1 15); do "
  cmd+="  t=\$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true); "
  cmd+="  [[ -n \"\$t\" ]] && break; "
  cmd+="  t=\$(timeout 2s xsel --clipboard --output 2>/dev/null || true); "
  cmd+="  [[ -n \"\$t\" ]] && break; "
  cmd+="  sleep 0.08; "
  cmd+="done; "
  cmd+="printf '%s' \"\$t\""

  "$HOST_EXEC" "$cmd"
}

copy_messages() {
  local t=""
  local bytes=0
  local attempt=1
  local method="click"
  local y_pct=35
  local jitter=0
  while [[ "$attempt" -le "$COPY_MESSAGES_ATTEMPTS" ]]; do
    read -r y_pct jitter < <(messages_click_params "$attempt")
    if [[ -x "$CLICK_MESSAGES" ]]; then
      t="$(CHATGPT_MESSAGES_CLICK_Y_PCT="$y_pct" CHATGPT_MESSAGES_CLICK_JITTER_PX="$jitter" CHATGPT_WID_HEX="$WID_HEX" "$CLICK_MESSAGES" 2>/dev/null || true)"
      method="click"
    else
      local mx my
      mx=$(( WIDTH * 55 / 100 ))
      my=$(( HEIGHT * y_pct / 100 ))
      t="$(copy_at "$mx" "$my")"
      method="coords"
    fi
    bytes="$(bytes_len "$t")"
    if [[ "$bytes" -gt 0 ]]; then
      break
    fi
    # Phase 4 meta
    printf '__LUCY_COPY_META__ COPY_MESSAGES_ATTEMPT_%s_BYTES=0\n' "$attempt" >&2
    sleep "$(copy_backoff "$attempt")"
    attempt=$((attempt + 1))
  done
  local attempts_used="$attempt"
  if [[ "$bytes" -eq 0 ]] && [[ "$attempt" -gt 1 ]]; then
    attempts_used=$((attempt - 1))
  fi
  printf '__LUCY_COPY_META__ COPY_MESSAGES_ATTEMPTS=%s COPY_MESSAGES_METHOD=%s COPY_MESSAGES_BYTES=%s\n' \
    "$attempts_used" "$method" "$bytes" >&2
  if [[ "$bytes" -eq 0 ]]; then
    printf '__LUCY_COPY_META__ COPY_MESSAGES_EMPTY=1\n' >&2
  fi
  printf '%s' "$t"
}

copy_input_safe() {
  local ix iy
  ix=$(( WIDTH * 70 / 100 ))
  iy=$(( HEIGHT - 220 ))
  copy_at "$ix" "$iy"
}

copy_input_probe() {
  local t=""
  if [[ -x "$ENSURE_FOCUS" ]]; then
    if t="$(FOCUS_RETURN_COPY=1 CHATGPT_WID_HEX="$WID_HEX" "$ENSURE_FOCUS" 2>/dev/null)"; then
      printf '__LUCY_COPY_META__ COPY_INPUT_PROBE_USED=1\n' >&2
    else
      printf '__LUCY_COPY_META__ COPY_INPUT_FOCUS_FAIL=1\n' >&2
      t=""
    fi
  else
    t=""
  fi
  printf '%s' "$t"
}

copy_input() {
  local t=""
  local bytes=0
  local attempt=1
  while [[ "$attempt" -le "$COPY_INPUT_ATTEMPTS" ]]; do
    t="$(copy_input_safe)"
    bytes="$(bytes_len "$t")"
    if [[ "$bytes" -gt 0 ]]; then
      break
    fi
    # Phase 4 meta
    printf '__LUCY_COPY_META__ COPY_INPUT_ATTEMPT_%s_BYTES=0\n' "$attempt" >&2
    sleep "$(copy_backoff "$attempt")"
    attempt=$((attempt + 1))
  done
  if [[ "$bytes" -eq 0 ]] && [[ "$COPY_INPUT_PROBE" -eq 1 ]]; then
    t="$(copy_input_probe)"
    bytes="$(bytes_len "$t")"
  fi
  local attempts_used="$attempt"
  if [[ "$bytes" -eq 0 ]] && [[ "$attempt" -gt 1 ]]; then
    attempts_used=$((attempt - 1))
  fi
  printf '__LUCY_COPY_META__ COPY_INPUT_ATTEMPTS=%s COPY_INPUT_BYTES=%s\n' \
    "$attempts_used" "$bytes" >&2
  if [[ "$bytes" -eq 0 ]]; then
    printf '__LUCY_COPY_META__ COPY_INPUT_EMPTY=1\n' >&2
  fi
  printf '%s' "$t"
}

txt1=""
txt2=""
bytes1=0
bytes2=0
mode="${COPY_MODE}"
chosen="messages"
best=""
bestBytes=0

if [[ "$mode" == "messages" ]]; then
  txt2="$(copy_messages)"
  bytes2="$(bytes_len "$txt2")"
  chosen="messages"
  best="$txt2"
  bestBytes="$bytes2"
elif [[ "$mode" == "input" ]]; then
  txt1="$(copy_input)"
  bytes1="$(bytes_len "$txt1")"
  chosen="input"
  best="$txt1"
  bestBytes="$bytes1"
else
  txt1="$(copy_input)"
  bytes1="$(bytes_len "$txt1")"
  txt2="$(copy_messages)"
  bytes2="$(bytes_len "$txt2")"
  chosen="input"
  best="$txt1"
  bestBytes="$bytes1"
  if [[ "$bytes2" -gt "$bytes1" ]]; then
    chosen="messages"
    best="$txt2"
    bestBytes="$bytes2"
  fi
fi

if [[ "$mode" == "messages" ]] && [[ "$bestBytes" -eq 0 ]]; then
  printf '__LUCY_COPY_META__ COPY_BYTES_1=%s COPY_BYTES_2=%s COPY_CHOSEN=%s COPY_BYTES=%s COPY_MODE=%s\n' \
    "$bytes1" "$bytes2" "$chosen" "$bestBytes" "$mode" >&2
  printf 'ERROR: COPY_MESSAGES_ZERO\n' >&2
  exit 4
fi

printf '__LUCY_COPY_META__ COPY_BYTES_1=%s COPY_BYTES_2=%s COPY_CHOSEN=%s COPY_BYTES=%s COPY_MODE=%s\n' \
  "$bytes1" "$bytes2" "$chosen" "$bestBytes" "$mode" >&2
if [[ "$bestBytes" -lt 200 ]]; then
  printf '__LUCY_COPY_META__ COPY_WEAK=1\n' >&2
fi

out="$best"

meta_lines="$(printf '%s\n' "$out" | sed -n 's/^__LUCY_COPY_META__ //p')"
if [[ -n "${meta_lines:-}" ]]; then
  while IFS= read -r line; do
    [[ -n "$line" ]] && printf '%s\n' "$line" >&2
  done <<< "$meta_lines"
fi
copy_text="$(printf '%s\n' "$out" | sed '/^__LUCY_COPY_META__/d')"

raw_tmp="$(mktemp /tmp/lucy_copy_raw.XXXX.txt)"
pre_tmp="$(mktemp /tmp/lucy_copy_pre.XXXX.txt)"
norm_tmp="$(mktemp /tmp/lucy_copy_norm.XXXX.txt)"
counts_tmp="$(mktemp /tmp/lucy_copy_counts.XXXX.txt)"
cleanup() {
  rm -f "$raw_tmp" "$pre_tmp" "$norm_tmp" "$counts_tmp" 2>/dev/null || true
}
trap cleanup EXIT

printf '%s' "$copy_text" > "$raw_tmp"
before_bytes="$(wc -c < "$raw_tmp" 2>/dev/null || echo 0)"
: > "$counts_tmp"

python3 - "$raw_tmp" "$pre_tmp" "$counts_tmp" <<'PY'
import sys

raw_path, out_path, counts_path = sys.argv[1], sys.argv[2], sys.argv[3]
phrases = [
    ("SUBSTR_DROP_NOFILE", "Ningún archivo seleccionado"),
    ("SUBSTR_DROP_DISCLAIMER", "ChatGPT puede cometer errores. Comprueba la información importante."),
    ("SUBSTR_DROP_SKIP", "Saltar al contenido"),
    ("SUBSTR_DROP_HISTORY", "Historial del chat"),
]

try:
    text = open(raw_path, encoding="utf-8", errors="replace").read()
except Exception:
    text = ""

counts = {}
for key, phrase in phrases:
    counts[key] = text.count(phrase)
    if counts[key]:
        text = text.replace(phrase, "")

with open(out_path, "w", encoding="utf-8") as f:
    f.write(text)

with open(counts_path, "a", encoding="utf-8") as f:
    for key, val in counts.items():
        f.write(f"{key}={val}\n")
PY

awk -v counts="$counts_tmp" '
BEGIN {
  dedupe=0; filter=0; blanks_collapsed=0;
  prev="__NONE__"; blank_run=0;
}
{
  line=$0
  if (line=="Saltar al contenido" || line=="Historial del chat" || line=="Ningún archivo seleccionado" || line=="ChatGPT puede cometer errores. Comprueba la información importante.") {
    filter++
    next
  }
  if (line=="") {
    blank_run++
    if (blank_run>2) { blanks_collapsed++; next }
    print line
    prev=line
    next
  }
  blank_run=0
  if (line==prev) { dedupe++; next }
  print line
  prev=line
}
END {
  print "DEDUPE_DROPPED=" dedupe >> counts
  print "FILTER_DROPPED=" filter >> counts
  print "BLANKS_COLLAPSED=" blanks_collapsed >> counts
}
' "$pre_tmp" > "$norm_tmp"

after_bytes="$(wc -c < "$norm_tmp" 2>/dev/null || echo 0)"
printf 'COPY_NORM_BEFORE_BYTES=%s COPY_NORM_AFTER_BYTES=%s\n' "$before_bytes" "$after_bytes" >&2
cat "$counts_tmp" >&2

cat "$norm_tmp"
