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
COPY_MODE_Q="$(printf '%q' "${COPY_MODE}")"

out="$("$HOST_EXEC" "bash -lc '
set -euo pipefail
WID_HEX=\"$WID_HEX\"
WID_DEC=\$(printf \"%d\" \"\$WID_HEX\")

wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true
xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true
sleep 0.18

# cerrar overlays
xdotool key --clearmodifiers Escape 2>/dev/null || true
sleep 0.06

geo=\$(xdotool getwindowgeometry --shell \"\$WID_DEC\" 2>/dev/null || true)
eval \"\$geo\" || true
: \${WIDTH:=1200}
: \${HEIGHT:=900}

copy_at() {
  local px=\"\$1\" py=\"\$2\"
  xdotool mousemove --window \"\$WID_DEC\" \"\$px\" \"\$py\" click 1 2>/dev/null || true
  sleep 0.10
  xdotool key --clearmodifiers ctrl+a 2>/dev/null || true
  sleep 0.06
  xdotool key --clearmodifiers ctrl+c 2>/dev/null || true
  sleep 0.20

  local t=\"\"
  # leer clipboard (60 intentos cortos)
  for _ in \$(seq 1 60); do
    t=\$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true)
    if [[ -n \"\$t\" ]]; then break; fi
    t=\$(timeout 2s xsel --clipboard --output 2>/dev/null || true)
    if [[ -n \"\$t\" ]]; then break; fi
    sleep 0.06
  done

  printf \"%s\" \"\$t\"
}

bytes_len() {
  local t=\"\$1\"
  printf \"%s\" \"\$t\" | wc -c | tr -d \" \\n\"
}

# zonas: input (abajo-centro) y mensajes (medio-centro)
input_x=\$(( WIDTH * 50 / 100 ))
input_y=\$(( HEIGHT * 92 / 100 ))
msg_x=\$(( WIDTH * 50 / 100 ))
msg_y=\$(( HEIGHT * 55 / 100 ))

txt1=\"\$(copy_at \"\$input_x\" \"\$input_y\")\"
bytes1=\"\$(bytes_len \"\$txt1\")\"
txt2=\"\$(copy_at \"\$msg_x\" \"\$msg_y\")\"
bytes2=\"\$(bytes_len \"\$txt2\")\"

mode=${COPY_MODE_Q}
chosen=\"input\"
best=\"\$txt1\"
bestBytes=\"\$bytes1\"
if [[ \"\$mode\" == \"messages\" ]]; then
  chosen=\"messages\"
  best=\"\$txt2\"
  bestBytes=\"\$bytes2\"
elif [[ \"\$mode\" == \"input\" ]]; then
  chosen=\"input\"
  best=\"\$txt1\"
  bestBytes=\"\$bytes1\"
else
  if [[ \"\$bytes2\" -gt \"\$bytes1\" ]]; then
    chosen=\"messages\"
    best=\"\$txt2\"
    bestBytes=\"\$bytes2\"
  fi
fi

printf \"__LUCY_COPY_META__ COPY_BYTES_1=%s COPY_BYTES_2=%s COPY_CHOSEN=%s COPY_BYTES=%s COPY_MODE=%s\\n\" \"\$bytes1\" \"\$bytes2\" \"\$chosen\" \"\$bestBytes\" \"\$mode\"
if [[ \"\$bestBytes\" -lt 200 ]]; then
  printf \"__LUCY_COPY_META__ COPY_WEAK=1\\n\"
fi

printf \"%s\" \"\$best\"
'")"

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
