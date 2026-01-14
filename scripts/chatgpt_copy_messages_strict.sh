#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_WID="$ROOT/scripts/chatgpt_get_wid.sh"
CLICK_MESSAGES="$ROOT/scripts/chatgpt_click_messages_zone.sh"

WID_HEX="${1:-${CHATGPT_WID_HEX:-}}"
if [[ -z "${WID_HEX:-}" ]]; then
  WID_HEX="$("$GET_WID" 2>/dev/null || true)"
fi
if [[ -z "${WID_HEX:-}" ]]; then
  echo "ERROR_NO_WID" >&2
  exit 3
fi

WID_DEC="$(printf "%d" "$WID_HEX" 2>/dev/null || echo 0)"
if [[ "${WID_DEC}" -le 0 ]]; then
  echo "ERROR_INVALID_WID" >&2
  exit 3
fi

# Por defecto: el strict debe devolver algo "real" (evita falsos positivos tipo 90 bytes)
MIN_BYTES="${CHATGPT_STRICT_COPY_MIN_BYTES:-200}"

# Intentos: x_pct y_pct jitter_px (coords relativas a ventana)
ATTEMPTS=(
  "40 50 0"
  "45 45 4"
  "55 50 4"
  "40 35 6"
  "55 35 6"
)

# Heurísticas de “copié basura / sidebar / header”
LOGIN_PATTERNS=(
  "Iniciar sesión"
  "Registrarse gratuitamente"
  "Permanecer con la sesión cerrada"
  "Gracias por probar ChatGPT"
  "Sign in"
  "Sign up"
)

BAD_PATTERNS=(
  "Historial"
  "Nuevo chat"
  "ChatGPT Plus"
  "Upgrade plan"
  "Saltar al contenido"
  "Historial del chat"
)

bytes_len() {
  local t="$1"
  printf "%s" "$t" | wc -c | tr -d " \n"
}

trim_basic() {
  # preserva saltos de línea, solo recorta espacios por línea y CR
  sed -e 's/\r//g' -e 's/[[:space:]]\+$//' -e 's/^[[:space:]]\+//'
}

for attempt in "${ATTEMPTS[@]}"; do
  read -r x_pct y_pct jitter <<< "$attempt"

  # Reusar el mecanismo ya robusto (Escape + retries largos + clipboard)
  t="$(CHATGPT_MESSAGES_CLICK_X_PCT="$x_pct" \
       CHATGPT_MESSAGES_CLICK_Y_PCT="$y_pct" \
       CHATGPT_MESSAGES_CLICK_JITTER_PX="$jitter" \
       CHATGPT_WID_HEX="$WID_HEX" \
       "$CLICK_MESSAGES" 2>/dev/null || true)"

  cleaned="$(printf "%s" "$t" | trim_basic)"
  # Fail-fast si estamos deslogueados/bloqueados (evita loops eternos)
  for lp in "${LOGIN_PATTERNS[@]}"; do
    if [[ "$cleaned" == *"$lp"* ]]; then
      echo "ERROR_BLOCKED_LOGIN: ChatGPT no está en modo chat (login/bloqueo detectado)" >&2
      exit 7
    fi
  done

  b="$(bytes_len "$cleaned")"

  is_bad=0

  if [[ "$b" -lt "$MIN_BYTES" ]]; then
    is_bad=1
  fi

  for pat in "${BAD_PATTERNS[@]}"; do
    if [[ "$cleaned" == *"$pat"* ]]; then
      is_bad=1
      break
    fi
  done

  if [[ "$is_bad" -eq 0 ]]; then
    echo "__LUCY_COPY_META__ OK x_pct=$x_pct y_pct=$y_pct jitter=$jitter bytes=$b" >&2
    printf "%s" "$cleaned"
    exit 0
  fi

  echo "WARN: strict copy attempt failed (empty/sidebar/weak) at ${x_pct}%,${y_pct}% bytes=$b" >&2
done

echo "ERROR: strict copy failed after all attempts" >&2
exit 1
