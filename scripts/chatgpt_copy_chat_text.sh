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

"$HOST_EXEC" "bash -lc '
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

best=\"\"
bestLen=0

try_copy() {
  local px=\"\$1\" py=\"\$2\"
  # click DENTRO del panel de mensajes (lado derecho) y copiar
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

  local l=\${#t}
  if [[ \"\$l\" -gt \"\$bestLen\" ]]; then
    bestLen=\"\$l\"
    best=\"\$t\"
  fi
}

# 3 anclas: bien a la derecha (evita sidebar) en distintas alturas
x1=\$(( WIDTH * 78 / 100 ))
x2=\$(( WIDTH * 88 / 100 ))
y1=\$(( HEIGHT * 28 / 100 ))
y2=\$(( HEIGHT * 45 / 100 ))
y3=\$(( HEIGHT * 62 / 100 ))

try_copy \"\$x1\" \"\$y1\"
try_copy \"\$x1\" \"\$y2\"
try_copy \"\$x2\" \"\$y2\"
try_copy \"\$x1\" \"\$y3\"

printf \"%s\" \"\$best\"
'"
