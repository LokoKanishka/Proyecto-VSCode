#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Consistencia X11
if [[ -f "$SCRIPT_DIR/x11_env.sh" ]]; then
  # shellcheck disable=SC1091
  source "$SCRIPT_DIR/x11_env.sh"
fi

# Override manual (útil para tests o para fijarlo desde voz)
if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
  echo "$CHATGPT_WID_HEX"
  exit 0
fi

mapfile -t LINES < <(wmctrl -l 2>/dev/null || true)
if [[ ${#LINES[@]} -eq 0 ]]; then
  echo "chatgpt_get_wid: wmctrl no devolvió ventanas (¿X11 disponible?)" >&2
  exit 1
fi

get_title() {
  # wmctrl: WID DESKTOP HOST TITLE...
  awk '{$1=$2=$3=""; sub(/^ +/,""); print}'
}

# 1) Preferencia absoluta: el chat puente “limpio”
for line in "${LINES[@]}"; do
  wid="$(awk '{print $1}' <<<"$line")"
  title="$(get_title <<<"$line")"
  if [[ "$title" == "ChatGPT - Google Chrome" ]]; then
    echo "$wid"
    exit 0
  fi
done

# 2) ChatGPT en Chrome pero excluyendo el perfil “V.S.Code”
for line in "${LINES[@]}"; do
  wid="$(awk '{print $1}' <<<"$line")"
  title="$(get_title <<<"$line")"
  if [[ "$title" == *ChatGPT* && "$title" == *"Google Chrome"* && "$title" != *"V.S.Code"* ]]; then
    echo "$wid"
    exit 0
  fi
done

# 3) Fallback: cualquier ChatGPT
for line in "${LINES[@]}"; do
  wid="$(awk '{print $1}' <<<"$line")"
  title="$(get_title <<<"$line")"
  if [[ "$title" == *ChatGPT* ]]; then
    echo "$wid"
    exit 0
  fi
done

echo "chatgpt_get_wid: no encontré ninguna ventana de ChatGPT" >&2
exit 1
