#!/usr/bin/env bash
set -euo pipefail

# Selector estable del WID de la ventana "puente" de ChatGPT.
# - NO usa wmctrl local: usa host_exec (IPC), sirve desde sandbox.
# - Si no existe ventana ChatGPT, la crea (abre chat.openai.com) y espera.
# - Protege de tipear en ventanas "V.S.Code ..."

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin}"
TITLE_INCLUDE="${CHATGPT_TITLE_INCLUDE:-ChatGPT}"
TITLE_EXCLUDE="${CHATGPT_TITLE_EXCLUDE:-V.S.Code}"

# Si ya está forzado por env, respetarlo.
if [[ -n "${CHATGPT_WID_HEX:-}" ]]; then
  printf '%s\n' "$CHATGPT_WID_HEX"
  exit 0
fi

get_wmctrl() {
  "$HOST_EXEC" 'wmctrl -l' 2>/dev/null || true
}

get_wmctrl_lx() {
  "$HOST_EXEC" 'wmctrl -lx' 2>/dev/null || true
}

read_pin_wid() {
  local f="$1"
  local line wid=""
  [[ -f "$f" ]] || return 1
  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    if [[ "$line" =~ (0x[0-9a-fA-F]+) ]]; then
      wid="${BASH_REMATCH[1]}"
      break
    fi
  done < "$f"
  if [[ -n "${wid:-}" ]]; then
    printf '%s\n' "$wid"
    return 0
  fi
  return 1
}

write_pin() {
  local wid="$1"
  local title="$2"
  mkdir -p "$(dirname "$PIN_FILE")"
  {
    echo "$wid"
    echo "TITLE=$title"
  } > "$PIN_FILE"
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

list_candidates_no_include() {
  awk -v exc="$TITLE_EXCLUDE" '
    {
      wid=$1;
      klass=$3;
      title="";
      for(i=5;i<=NF;i++){ title = title (i==5 ? "" : " ") $i }
      if(tolower(klass) !~ /chrome/) next;
      if(exc!="" && index(title,exc)>0) next;
      printf "%s\t%s\n", wid, title
    }
  '
}

get_active_wid() {
  local raw
  raw="$("$HOST_EXEC" 'xprop -root _NET_ACTIVE_WINDOW' 2>/dev/null \
    | sed -n 's/.*\(0x[0-9a-fA-F]\+\).*/\1/p' | head -n 1)"
  if [[ -n "${raw:-}" ]]; then
    printf '0x%08x\n' "$((raw))"
  fi
}

get_title_by_wid() {
  local wid="$1"
  local wins
  wins="$(get_wmctrl)"
  awk -v w="$wid" '$1==w { $1=""; $2=""; $3=""; sub(/^ +/, ""); print; exit }' <<< "$wins"
}

wid_exists() {
  local wid="$1"
  [[ -n "${wid:-}" ]] || return 1
  if "$HOST_EXEC" "xdotool getwindowname ${wid}" >/dev/null 2>&1; then
    return 0
  fi
  "$HOST_EXEC" "wmctrl -l | awk '{print \\$1}' | grep -Fxq \"${wid}\"" >/dev/null 2>&1
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

PIN_RECOVER_NEEDS_WRITE=0

# Pin file handling (if present)
if [[ -f "${PIN_FILE}" ]]; then
  PIN_WID="$(read_pin_wid "$PIN_FILE" || true)"
  if [[ -n "${PIN_WID:-}" ]]; then
    if ! wid_exists "$PIN_WID"; then
      echo "PIN_INVALID=1 old_wid=${PIN_WID}" >&2
      PIN_RECOVER_NEEDS_WRITE=1
      rm -f "$PIN_FILE" 2>/dev/null || true
      PIN_WID=""
    fi
    if [[ -n "${PIN_WID:-}" ]]; then
      TITLE_PIN="$(get_title_by_wid "$PIN_WID")"
      PIN_TITLE_STORED="$(sed -n 's/^TITLE=//p' "$PIN_FILE" | head -n 1)"
      pin_valid=0
      if [[ -n "${TITLE_PIN:-}" ]] && [[ "${TITLE_PIN}" == *"${TITLE_INCLUDE}"* ]] && [[ "${TITLE_PIN}" != *"${TITLE_EXCLUDE}"* ]]; then
        pin_valid=1
      elif [[ -n "${PIN_TITLE_STORED:-}" ]] && [[ "${PIN_TITLE_STORED}" == *"${TITLE_INCLUDE}"* ]] && [[ "${PIN_TITLE_STORED}" != *"${TITLE_EXCLUDE}"* ]]; then
        pin_valid=1
      fi
      if [[ "${pin_valid}" -eq 1 ]]; then
        printf 'WID_CHOSEN=%s TITLE=%s\n' "$PIN_WID" "${TITLE_PIN:-$PIN_TITLE_STORED}" >&2
        printf '%s\n' "$PIN_WID"
        exit 0
      fi
      if [[ "${CHATGPT_WID_PIN_ONLY:-0}" -eq 1 ]]; then
        echo "ERROR: PIN_INVALID WID=${PIN_WID} TITLE=${TITLE_PIN} PIN_TITLE=${PIN_TITLE_STORED}" >&2
        exit 3
      fi
      echo "WARN: PIN_INVALID WID=${PIN_WID} TITLE=${TITLE_PIN} PIN_TITLE=${PIN_TITLE_STORED} (fallback)" >&2
    fi
  fi
fi

# 1) Intento directo
WINS="$(get_wmctrl)"
CANDIDATES="$(printf '%s\n' "$WINS" | list_candidates)"
if [[ -z "${CANDIDATES:-}" ]] && [[ "${PIN_RECOVER_NEEDS_WRITE}" -eq 1 ]]; then
  WINS_LX="$(get_wmctrl_lx)"
  CANDIDATES="$(printf '%s\n' "$WINS_LX" | list_candidates_no_include)"
fi
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
  if [[ "${PIN_RECOVER_NEEDS_WRITE}" -eq 1 ]]; then
    "$ROOT/scripts/chatgpt_unpin_wid.sh" >/dev/null 2>&1 || true
    "$ROOT/scripts/chatgpt_pin_wid.sh" >/dev/null
    WID="$(read_pin_wid "$PIN_FILE" || true)"
    if [[ -n "${WID:-}" ]]; then
      echo "PIN_RECOVERED=1 new_wid=${WID}" >&2
      PIN_RECOVER_NEEDS_WRITE=0
    fi
  fi
fi

if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no encuentro ventana ChatGPT (título no contiene '${TITLE_INCLUDE}'). Abrí ChatGPT en Chrome y reintentá." >&2
  exit 3
fi

if [[ "${PIN_RECOVER_NEEDS_WRITE}" -eq 1 ]]; then
  TITLE_RECOVER="$(get_title_by_wid "$WID")"
  PIN_TITLE="$TITLE_RECOVER"
  if [[ -n "${TITLE_INCLUDE:-}" ]] && [[ "${TITLE_RECOVER}" != *"${TITLE_INCLUDE}"* ]]; then
    PIN_TITLE="$TITLE_INCLUDE"
  fi
  write_pin "$WID" "$PIN_TITLE"
  echo "PIN_RECOVERED=1 new_wid=${WID}" >&2
fi

printf '%s\n' "$WID"
