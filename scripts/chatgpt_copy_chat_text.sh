#!/usr/bin/env bash
set -euo pipefail

# Copia texto visible de la ventana ChatGPT (bridge) al stdout usando Ctrl+A/Ctrl+C
# Robusto contra foco en omnibox/input: fuerza web-content con F6x2 + click en zona segura.

WID_HEX="${CHATGPT_WID_HEX:-${1:-}}"
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR: seteá CHATGPT_WID_HEX (ej: 0x04400004) o pasalo como arg" >&2
  exit 2
fi

# decimal para xdotool
WID_DEC=$((16#${WID_HEX#0x}))

# activar
wmctrl -ia "$WID_HEX" >/dev/null 2>&1 || true
xdotool windowactivate --sync "$WID_DEC" >/dev/null 2>&1 || true
sleep 0.12

# geometry
eval "$(xdotool getwindowgeometry --shell "$WID_DEC" 2>/dev/null || true)"
# defaults por si falla
X="${X:-0}"; Y="${Y:-0}"; WIDTH="${WIDTH:-900}"; HEIGHT="${HEIGHT:-900}"

# punto de click: centro horizontal, 30% vertical, pero nunca arriba de 170px (evita omnibox)
cx=$((WIDTH/2))
cy=$(((HEIGHT*30)/100))
if [[ "$cy" -lt 170 ]]; then cy=170; fi
# margen inferior
if [[ "$cy" -gt $((HEIGHT-120)) ]]; then cy=$((HEIGHT-120)); fi

# limpiar overlays / sacar foco raro
xdotool key --clearmodifiers Escape >/dev/null 2>&1 || true
sleep 0.05

# F6 suele alternar: omnibox <-> contenido web. Lo mandamos 2 veces.
xdotool key --clearmodifiers F6 >/dev/null 2>&1 || true
sleep 0.05
xdotool key --clearmodifiers F6 >/dev/null 2>&1 || true
sleep 0.05

# click en zona “web content”
xdotool mousemove --window "$WID_DEC" "$cx" "$cy" click 1 >/dev/null 2>&1 || true
sleep 0.08

# seleccionar todo + copiar
xdotool key --clearmodifiers ctrl+a >/dev/null 2>&1 || true
sleep 0.06
xdotool key --clearmodifiers ctrl+c >/dev/null 2>&1 || true
sleep 0.18

# leer clipboard (reintentos cortos)
text=""
for _ in $(seq 1 60); do
  text="$(timeout 2s xclip -selection clipboard -o 2>/dev/null || true)"
  [[ -n "${text:-}" ]] && break
  text="$(timeout 2s xsel --clipboard --output 2>/dev/null || true)"
  [[ -n "${text:-}" ]] && break
  sleep 0.08
done

printf '%s\n' "${text:-}"
