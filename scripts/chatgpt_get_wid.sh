#!/usr/bin/env bash
set -euo pipefail

# Selector estable del WID de la ventana "puente" de ChatGPT.
# - NO usa wmctrl local: usa host_exec (IPC), sirve desde sandbox.
# - Si no existe ventana ChatGPT, la crea (abre chat.openai.com) y espera.
# - Protege de tipear en ventanas "V.S.Code ..."

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

# Si ya está forzado por env, respetarlo.
if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
  printf '%s\n' "$CHATGPT_WID_HEX"
  exit 0
fi

get_wmctrl() {
  "$HOST_EXEC" 'wmctrl -l' 2>/dev/null || true
}

list_candidates() {
  awk -v inc="$TITLE_INCLUDE" -v exc="$TITLE_EXCLUDE" '
    {
      wid=$1;
      title="";
      for(i=4;i<=NF;i++){ title = title (i==4 ? "" : " ") $i }
      if(inc!="" && index(title,inc)==0) next;
      if(exc!="" && index(title,exc)>0) next;
      printf "%s\t%s\n", wid, title
    }
  '
}

get_active_wid() {
  "$HOST_EXEC" 'xprop -root _NET_ACTIVE_WINDOW' 2>/dev/null \
    | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1
}

choose_wid() {
  local candidates="$1"
  local active="$2"
  local chosen=""
  local chosen_title=""

  if [[ -n "${active:-}" ]] && printf '%s\n' "$candidates" | awk -v a="$active" -F '\t' '$1==a{exit 0} END{exit 1}'; then
    chosen="$active"
    chosen_title="$(printf '%s\n' "$candidates" | awk -v a="$active" -F '\t' '$1==a{print $2; exit}')"
  else
    local max_dec=-1
    local max_wid=""
    local max_title=""
    while IFS=$'\t' read -r wid title; do
      [[ -z "${wid:-}" ]] && continue
      dec="$(printf "%d" "$wid" 2>/dev/null || echo -1)"
      if [[ "$dec" -gt "$max_dec" ]]; then
        max_dec="$dec"
        max_wid="$wid"
        max_title="$title"
      fi
    done <<< "$candidates"
    chosen="$max_wid"
    chosen_title="$max_title"
  fi

  if [[ -n "${chosen:-}" ]]; then
    printf 'WID_CHOSEN=%s TITLE=%s\n' "$chosen" "$chosen_title" >&2
    printf '%s\n' "$chosen"
  fi
}

TITLE_INCLUDE="${CHATGPT_TITLE_INCLUDE:-ChatGPT}"
TITLE_EXCLUDE="${CHATGPT_TITLE_EXCLUDE:-V.S.Code}"

# 1) Intento directo
WINS="$(get_wmctrl)"
CANDIDATES="$(printf '%s\n' "$WINS" | list_candidates)"
WID="$(choose_wid "$CANDIDATES" "$(get_active_wid)")"

# 2) Si no hay ventana ChatGPT, abrirla y esperar (si no está deshabilitado)
if [[ -z "${WID:-}" ]]; then
  if [[ "${CHATGPT_GET_WID_NOOPEN:-0}" -eq 1 ]]; then
    echo "ERROR: NO_CANDIDATE_WID" >&2
    exit 3
  fi
  "$HOST_EXEC" "bash -lc 'google-chrome --new-window \"https://chat.openai.com/\" >/dev/null 2>&1 & disown'" >/dev/null 2>&1 || true

  for _ in $(seq 1 15); do
    sleep 1
    WINS="$(get_wmctrl)"
    CANDIDATES="$(printf '%s\n' "$WINS" | list_candidates)"
    WID="$(choose_wid "$CANDIDATES" "$(get_active_wid)")"
    [[ -n "${WID:-}" ]] && break
  done
fi

# 3) Resultado
if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no encuentro ventana ChatGPT (título no contiene '${TITLE_INCLUDE}'). Abrí ChatGPT en Chrome y reintentá." >&2
  exit 3
fi

printf '%s\n' "$WID"
