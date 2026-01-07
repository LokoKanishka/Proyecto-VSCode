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
TITLE_EXCLUDE="${CHATGPT_TITLE_EXCLUDE:-}"
CHATGPT_OPEN_URL="${CHATGPT_OPEN_URL:-https://chat.openai.com/}"

dbg() {
  if [[ "${CHATGPT_WID_DEBUG:-0}" == "1" ]]; then
    echo "$*" >&2
  fi
  return 0
}

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

get_stack_order() {
  # Returns a list of WIDs in stacking order (bottom -> top). We prefer the last match.
  "$HOST_EXEC" 'xprop -root _NET_CLIENT_LIST_STACKING' 2>/dev/null \
    | sed -n 's/.*# //p' \
    | tr ',' '\n' \
    | awk '{
        gsub(/^[[:space:]]+|[[:space:]]+$/,"");
        if ($0 ~ /^0x[0-9a-fA-F]+$/) print $0
      }' || true
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

title_is_excluded() {
  local title_lc
  title_lc="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  if [[ -n "${TITLE_EXCLUDE:-}" ]]; then
    local exc_lc
    exc_lc="$(printf '%s' "${TITLE_EXCLUDE}" | tr '[:upper:]' '[:lower:]')"
    [[ "${title_lc}" == *"${exc_lc}"* ]] && return 0
  fi
  [[ "${title_lc}" == *"v.s.code"* ]] && return 0
  [[ "${title_lc}" == *"visual studio code"* ]] && return 0
  return 1
}

title_has_strong_hint() {
  local title_lc
  title_lc="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  [[ "${title_lc}" == *"chatgpt"* ]] && return 0
  [[ "${title_lc}" == *"openai"* ]] && return 0
  [[ "${title_lc}" == *"chat.openai"* ]] && return 0
  [[ "${title_lc}" == *"chatgpt.com"* ]] && return 0
  return 1
}

list_chrome_candidates() {
  get_wmctrl_lx | awk '
    {
      wid=$1;
      klass=$3;
      title="";
      for(i=5;i<=NF;i++){ title = title (i==5 ? "" : " ") $i }
      if(tolower(klass) !~ /(google-chrome|chromium)/) next;
      printf "%s\t%s\n", wid, title
    }
  ' | while IFS=$'\t' read -r wid title; do
    [[ -z "${wid:-}" ]] && continue
    if title_is_excluded "$title"; then
      continue
    fi
    printf "%s\t%s\n" "$wid" "$title"
  done
}

list_strong_candidates() {
  list_chrome_candidates | while IFS=$'\t' read -r wid title; do
    [[ -z "${wid:-}" ]] && continue
    if title_has_strong_hint "$title"; then
      printf "%s\t%s\n" "$wid" "$title"
    fi
  done
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

wid_is_chrome() {
  local wid="$1"
  local klass=""
  klass="$(get_wmctrl_lx | awk -v w="$wid" '$1==w {print $3; exit}')"
  [[ -n "${klass:-}" ]] || return 1
  case "${klass,,}" in
    *google-chrome*|*chromium*)
      return 0
      ;;
  esac
  return 1
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

  [[ -n "${candidates:-}" ]] || return 0

  # Build map wid -> title for fast membership checks
  declare -A cand_title=()
  while IFS=$'\t' read -r wid title; do
    [[ -z "${wid:-}" ]] && continue
    cand_title["$wid"]="$title"
  done <<< "$candidates"

  # 1) Prefer active if it is a candidate
  if [[ -n "${active:-}" ]] && [[ -n "${cand_title[$active]:-}" ]]; then
    chosen="$active"
    chosen_title="${cand_title[$active]}"
  else
    # 2) Prefer top-most candidate in stacking order
    local stack top=""
    stack="$(get_stack_order)"
    if [[ -n "${stack:-}" ]]; then
      while IFS= read -r w; do
        [[ -z "${w:-}" ]] && continue
        if [[ -n "${cand_title[$w]:-}" ]]; then
          top="$w"
        fi
      done <<< "$stack"
      if [[ -n "${top:-}" ]]; then
        chosen="$top"
        chosen_title="${cand_title[$top]}"
      fi
    fi

    # 3) Fallback: highest numeric WID (old behavior)
    if [[ -z "${chosen:-}" ]]; then
      local max_dec=-1
      local max_wid=""
      local max_title=""
      local dec
      for w in "${!cand_title[@]}"; do
        dec="$(printf "%d" "$w" 2>/dev/null || echo -1)"
        if [[ "$dec" -gt "$max_dec" ]]; then
          max_dec="$dec"
          max_wid="$w"
          max_title="${cand_title[$w]}"
        fi
      done
      chosen="$max_wid"
      chosen_title="$max_title"
    fi
  fi

  if [[ -n "${chosen:-}" ]]; then
    dbg "WID_CHOSEN=${chosen} TITLE=${chosen_title}"
    printf '%s\n' "$chosen"
  fi
}

choose_latest_wid() {
  local candidates="$1"
  local max_dec=-1
  local max_wid=""
  local max_title=""
  local dec
  while IFS=$'\t' read -r wid title; do
    [[ -z "${wid:-}" ]] && continue
    dec="$(printf "%d" "$wid" 2>/dev/null || echo -1)"
    if [[ "$dec" -gt "$max_dec" ]]; then
      max_dec="$dec"
      max_wid="$wid"
      max_title="$title"
    fi
  done <<< "$candidates"
  if [[ -n "${max_wid:-}" ]]; then
    dbg "WID_CHOSEN=${max_wid} TITLE=${max_title}"
    printf '%s\n' "$max_wid"
  fi
}

filter_new_candidates() {
  local before="$1"
  local candidates="$2"
  local wid title
  while IFS=$'\t' read -r wid title; do
    [[ -z "${wid:-}" ]] && continue
    if grep -Fxq "${wid}" <<< "${before}"; then
      continue
    fi
    printf '%s\t%s\n' "$wid" "$title"
  done <<< "$candidates"
}

open_chatgpt_window() {
  "$HOST_EXEC" "bash -lc 'google-chrome --new-window \"${CHATGPT_OPEN_URL}\" >/dev/null 2>&1 & disown'" \
    >/dev/null 2>&1 || true
}

open_chatgpt_and_pick_new() {
  local before candidates new_candidates wid
  before="$(list_chrome_candidates | awk -F '\t' '{print $1}')"
  open_chatgpt_window
  for _ in $(seq 1 15); do
    sleep 1
    candidates="$(list_chrome_candidates)"
    new_candidates="$(filter_new_candidates "$before" "$candidates")"
    if [[ -n "${new_candidates:-}" ]]; then
      wid="$(choose_latest_wid "$new_candidates")"
      [[ -n "${wid:-}" ]] && printf '%s\n' "$wid" && return 0
    fi
  done
  candidates="$(list_chrome_candidates)"
  wid="$(choose_latest_wid "$candidates")"
  [[ -n "${wid:-}" ]] && printf '%s\n' "$wid" && return 0
  return 1
}

PIN_RECOVER_NEEDS_WRITE=0

# Pin file handling (if present)
if [[ -f "${PIN_FILE}" ]]; then
  PIN_WID="$(read_pin_wid "$PIN_FILE" || true)"
  if [[ -n "${PIN_WID:-}" ]]; then
    if wid_exists "$PIN_WID" && wid_is_chrome "$PIN_WID"; then
      TITLE_PIN="$(get_title_by_wid "$PIN_WID")"
      if ! title_is_excluded "${TITLE_PIN:-}"; then
        if [[ -z "${TITLE_PIN:-}" ]]; then
          TITLE_PIN="${TITLE_INCLUDE}"
        fi
        write_pin "$PIN_WID" "$TITLE_PIN"
        dbg "WID_CHOSEN=${PIN_WID} TITLE=${TITLE_PIN}"
        printf '%s\n' "$PIN_WID"
        exit 0
      fi
    fi
    echo "PIN_INVALID=1 old_wid=${PIN_WID}" >&2
    if [[ "${CHATGPT_WID_PIN_ONLY:-0}" -eq 1 ]]; then
      echo "ERROR: PIN_INVALID WID=${PIN_WID}" >&2
      exit 3
    fi
    rm -f "$PIN_FILE" 2>/dev/null || true
    PIN_RECOVER_NEEDS_WRITE=1
  fi
fi

if [[ "${PIN_RECOVER_NEEDS_WRITE}" -eq 1 ]]; then
  STRONG_CANDIDATES="$(list_strong_candidates)"
  strong_count="$(printf '%s\n' "$STRONG_CANDIDATES" | awk 'NF{c++} END{print c+0}')"
  RECOVER_WID=""
  if [[ "${strong_count}" -eq 1 ]]; then
    RECOVER_WID="$(printf '%s\n' "$STRONG_CANDIDATES" | head -n 1 | cut -f1)"
  else
    if [[ "${CHATGPT_GET_WID_NOOPEN:-0}" -eq 1 ]]; then
      echo "ERROR: PIN_INVALID and recovery needs new window (CHATGPT_GET_WID_NOOPEN=1)" >&2
      exit 3
    fi
    RECOVER_WID="$(open_chatgpt_and_pick_new || true)"
  fi

  if [[ -z "${RECOVER_WID:-}" ]]; then
    echo "ERROR: PIN_INVALID and recovery failed" >&2
    exit 3
  fi

  TITLE_RECOVER="$(get_title_by_wid "$RECOVER_WID")"
  if [[ -z "${TITLE_RECOVER:-}" ]]; then
    TITLE_RECOVER="${TITLE_INCLUDE}"
  fi
  write_pin "$RECOVER_WID" "$TITLE_RECOVER"
  echo "PIN_RECOVERED=1 new_wid=${RECOVER_WID}" >&2
  printf '%s\n' "$RECOVER_WID"
  exit 0
fi

# 1) Selección normal
CANDIDATES="$(list_chrome_candidates)"
WID="$(choose_wid "$CANDIDATES" "$(get_active_wid)")"

# 2) Si no hay ventana Chrome, abrir ChatGPT y esperar (si no está deshabilitado)
if [[ -z "${WID:-}" ]]; then
  if [[ "${CHATGPT_GET_WID_NOOPEN:-0}" -eq 1 ]]; then
    echo "ERROR: NO_CANDIDATE_WID" >&2
    exit 3
  fi
  WID="$(open_chatgpt_and_pick_new || true)"
fi

if [[ -z "${WID:-}" ]]; then
  echo "ERROR: no encuentro ventana ChatGPT en Chrome. Abrí ChatGPT y reintentá." >&2
  exit 3
fi

printf '%s\n' "$WID"
