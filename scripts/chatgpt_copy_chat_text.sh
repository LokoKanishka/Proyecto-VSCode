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

chosen=\"input\"
best=\"\$txt1\"
bestBytes=\"\$bytes1\"
if [[ \"\$bytes2\" -gt \"\$bytes1\" ]]; then
  chosen=\"messages\"
  best=\"\$txt2\"
  bestBytes=\"\$bytes2\"
fi

printf \"__LUCY_COPY_META__ COPY_BYTES_1=%s COPY_BYTES_2=%s COPY_CHOSEN=%s COPY_BYTES=%s\\n\" \"\$bytes1\" \"\$bytes2\" \"\$chosen\" \"\$bestBytes\"
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
printf '%s' "$copy_text"
