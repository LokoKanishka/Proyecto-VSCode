#!/usr/bin/env bash
set -euo pipefail

# A24_USE_CHATGPT_WID_HEX_IF_SET
if [ -n "${CHATGPT_WID_HEX:-}" ]; then
  if xprop -id "$CHATGPT_WID_HEX" _NET_WM_NAME >/dev/null 2>&1; then
    echo "WID_HEX=$CHATGPT_WID_HEX"
    echo "RC=0"
    exit 0
  fi
fi

# Selector estable del WID de la ventana "puente" de ChatGPT.
# - NO usa wmctrl local: usa host_exec (IPC), sirve desde sandbox.
# - Si no existe ventana ChatGPT, la crea (abre chat.openai.com) y espera.
# - Protege de tipear en ventanas "V.S.Code ..."

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

# A24_DIEGO_EMAIL_GATE_BEGIN
# Si estamos en modo "diego", exigimos email y pin del cliente Chrome.
CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-}"
CHATGPT_EXPECTED_EMAIL="${CHATGPT_EXPECTED_EMAIL:-}"
CHATGPT_WID_PIN_FILE="${CHATGPT_WID_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"
CHATGPT_ALLOW_ACTIVE_WINDOW="${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}"

if [[ "${CHATGPT_PROFILE_NAME,,}" == "diego" ]]; then
  : "${CHATGPT_EXPECTED_EMAIL:=chatjepetex2025@gmail.com}"
  export CHROME_PROFILE_NAME="${CHROME_PROFILE_NAME:-$CHATGPT_PROFILE_NAME}"
  export CHROME_DIEGO_EMAIL="${CHROME_DIEGO_EMAIL:-$CHATGPT_EXPECTED_EMAIL}"
  export CHROME_DIEGO_PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$CHATGPT_WID_PIN_FILE}"
  # Si no hay pin, lo generamos por guard del cliente (no por ventana activa)
  if [[ ! -s "$CHATGPT_WID_PIN_FILE" ]]; then
    "$ROOT/scripts/chrome_guard_diego_client.sh" "https://www.google.com/" >/dev/null
  fi
fi
# A24_DIEGO_EMAIL_GATE_END
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"
CHROME_OPEN="$ROOT/scripts/chatgpt_chrome_open.sh"
PAID_ENSURE="$ROOT/scripts/chatgpt_paid_ensure_chatgpt.sh"
CHATGPT_TARGET="${CHATGPT_TARGET:-paid}"
PROFILE_NAME="${CHATGPT_PROFILE_NAME:-free}"
DEFAULT_FREE_DIR="$HOME/.cache/lucy_chrome_chatgpt_free"
CHATGPT_CHROME_USER_DATA_DIR="${CHATGPT_CHROME_USER_DATA_DIR:-${CHATGPT_BRIDGE_PROFILE_DIR:-$DEFAULT_FREE_DIR}}"
FREE_PROFILE_DIR="${CHATGPT_FREE_PROFILE_DIR:-${CHATGPT_CHROME_USER_DATA_DIR:-$DEFAULT_FREE_DIR}}"
if [[ -z "${FREE_PROFILE_DIR:-}" ]]; then
  FREE_PROFILE_DIR="$DEFAULT_FREE_DIR"
fi
if [[ "${CHATGPT_TARGET}" == "paid" ]]; then
  CHATGPT_CHROME_USER_DATA_DIR=""
fi
PIN_FILE="${CHATGPT_WID_PIN_FILE:-$HOME/.cache/lucy_chatgpt_wid_pin_${CHATGPT_TARGET}}"
ensure_pin_file() {
  local f="$1"
  local dir
  dir="$(dirname "$f")"
  mkdir -p "$dir" 2>/dev/null || true
  if [[ -e "$f" ]]; then
    : >>"$f" 2>/dev/null || return 1
  else
    local tmp
    tmp="$(mktemp "$dir/.pinwrite.XXXX" 2>/dev/null)" || return 1
    rm -f "$tmp" 2>/dev/null || true
  fi
  return 0
}
if ! ensure_pin_file "$PIN_FILE"; then
  PIN_FILE="/tmp/lucy_chatgpt_wid_pin_${CHATGPT_TARGET}"
  mkdir -p "$(dirname "$PIN_FILE")" 2>/dev/null || true
  echo "WARN: PIN_FILE not writable, using ${PIN_FILE}" >&2
fi
export CHATGPT_WID_PIN_FILE="$PIN_FILE"

# PAID_PIN_TRUSTED: en paid, el título del tab puede NO contener "ChatGPT" (ej. "Hilo de prueba - Google Chrome").
# Si hay pinfile paid y el WID sigue existiendo, confiamos en el pin (solo aplicamos exclusions).
PAID_PIN_TRUSTED="${CHATGPT_PAID_PIN_TRUSTED:-1}"
CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS:-lucy-chatgpt-bridge}"
if [[ "${CHATGPT_TARGET}" == "dummy" ]]; then
  TITLE_INCLUDE="${CHATGPT_TITLE_INCLUDE:-LUCY Dummy Chat}"
else
  TITLE_INCLUDE="${CHATGPT_TITLE_INCLUDE:-ChatGPT}"
fi

TITLE_EXCLUDE="${CHATGPT_TITLE_EXCLUDE:-}"
CHATGPT_OPEN_URL="${CHATGPT_OPEN_URL:-https://chat.openai.com/}"
PROFILE_LOCK=0
if [[ "${CHATGPT_TARGET}" == "free" ]] && [[ -n "${CHATGPT_CHROME_USER_DATA_DIR:-}" ]]; then
  PROFILE_LOCK=1
  printf 'PROFILE_LOCK=1 user_data_dir=%s\n' "$CHATGPT_CHROME_USER_DATA_DIR" >&2
fi

DBG_COUNT=0
DBG_MAX="${CHATGPT_WID_DEBUG_MAX:-12}"
dbg() {
  if [[ "${CHATGPT_WID_DEBUG:-0}" == "1" ]]; then
    DBG_COUNT=$((DBG_COUNT + 1))
    if [[ "${DBG_COUNT}" -le "${DBG_MAX}" ]]; then
      echo "$*" >&2
    fi
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

get_wmctrl_lp() {
  "$HOST_EXEC" 'wmctrl -lp' 2>/dev/null || true
}

get_wm_command_by_wid() {
  local wid="$1"
  local out
  out="$("$HOST_EXEC" "xprop -id ${wid} WM_COMMAND" 2>/dev/null || true)"
  if [[ "${out}" == *"not found"* ]]; then
    return 0
  fi
  printf '%s\n' "$out"
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
  if [[ "${CHATGPT_TARGET}" == "paid" ]] && [[ "${title_lc}" == *"lucy dummy chat"* ]]; then
    return 0
  fi
  [[ "${title_lc}" == *"v.s.code"* ]] && return 0
  [[ "${title_lc}" == *"visual studio code"* ]] && return 0
  return 1
}

# Fast-path: paid usa pinfile (no requiere TITLE_INCLUDE)
if [[ "${CHATGPT_TARGET}" == "paid" ]] && [[ "${PAID_PIN_TRUSTED}" -eq 1 ]] && [[ -f "${PIN_FILE}" ]]; then
  # Leer primer campo (WID_HEX) y título (si existe) del pinfile
  pin_wid_hex="$(head -n 1 "${PIN_FILE}" 2>/dev/null | awk '{print $1}' || true)"
  if [[ -n "${pin_wid_hex:-}" ]]; then
    # Confirmar que la ventana existe y obtener título actual (vía host)
    pin_wid_dec="$(printf "%d" "${pin_wid_hex}" 2>/dev/null || echo 0)"
    if [[ "${pin_wid_dec}" -gt 0 ]]; then
      pin_title="$("$HOST_EXEC" "wmctrl -lx 2>/dev/null | awk -v w='${pin_wid_hex}' '\$1==w { \$1=\$2=\$3=\$4=\"\"; sub(/^ +/,\"\"); print; exit }'")"
      if [[ -z "${pin_title:-}" ]]; then
        pin_title="$("$HOST_EXEC" "xdotool getwindowname ${pin_wid_dec} 2>/dev/null")"
      fi
      # Aplicar SOLO exclusions (no include) para paid
      if [[ -n "${pin_title:-}" ]] && ! title_is_excluded "${pin_title}"; then
        printf "%s\n" "${pin_wid_hex}"
        exit 0
      fi
    fi
  fi
fi

title_is_included() {
  [[ -z "${TITLE_INCLUDE:-}" ]] && return 0
  local title_lc inc_lc
  title_lc="$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')"
  inc_lc="$(printf '%s' "${TITLE_INCLUDE}" | tr '[:upper:]' '[:lower:]')"
  [[ "${title_lc}" == *"${inc_lc}"* ]]
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
  get_wmctrl_lp | awk '
    {
      wid=$1;
      pid=$3;
      title="";
      for(i=5;i<=NF;i++){ title = title (i==5 ? "" : " ") $i }
      printf "%s\t%s\t%s\n", wid, pid, title
    }
  ' | while IFS=$'\t' read -r wid pid title; do
    [[ -z "${wid:-}" ]] && continue
    cmd="$(get_cmdline_by_pid "$pid")"
    if ! cmdline_is_chrome "$cmd"; then
      continue
    fi
    if ! cmdline_matches_profile "$cmd"; then
      continue
    fi
    if ! wm_command_matches_profile "$wid"; then
      continue
    fi
    if title_is_excluded "$title"; then
      continue
    fi
    if ! title_is_included "$title"; then
      continue
    fi
    printf "%s\t%s\t%s\n" "$wid" "$pid" "$title"
  done
}

list_paid_candidates() {
  get_wmctrl_lp | awk '
    {
      wid=$1;
      pid=$3;
      title="";
      for(i=5;i<=NF;i++){ title = title (i==5 ? "" : " ") $i }
      printf "%s\t%s\t%s\n", wid, pid, title
    }
  ' | while IFS=$'\t' read -r wid pid title; do
    [[ -z "${wid:-}" ]] && continue
    cmd="$(get_cmdline_by_pid "$pid")"
    if ! cmdline_is_chrome "$cmd"; then
      continue
    fi
    if cmdline_has_user_data_dir "$cmd" "$FREE_PROFILE_DIR"; then
      continue
    fi
    if title_is_excluded "$title"; then
      continue
    fi
    if ! title_is_included "$title"; then
      continue
    fi
    printf "%s\t%s\t%s\n" "$wid" "$pid" "$title"
  done
}

list_dummy_candidates() {
  get_wmctrl_lp | awk '
    {
      wid=$1;
      pid=$3;
      title="";
      for(i=5;i<=NF;i++){ title = title (i==5 ? "" : " ") $i }
      printf "%s\t%s\t%s\n", wid, pid, title
    }
  ' | while IFS=$'\t' read -r wid pid title; do
    [[ -z "${wid:-}" ]] && continue
    if [[ "${title}" != *"LUCY Dummy Chat"* ]]; then
      continue
    fi
    cmd="$(get_cmdline_by_pid "$pid")"
    if ! cmdline_is_chrome "$cmd"; then
      continue
    fi
    printf "%s\t%s\t%s\n" "$wid" "$pid" "$title"
  done
}

list_strong_candidates() {
  list_chrome_candidates | while IFS=$'\t' read -r wid pid title; do
    [[ -z "${wid:-}" ]] && continue
    if title_has_strong_hint "$title"; then
      printf "%s\t%s\t%s\n" "$wid" "$pid" "$title"
    fi
  done
}

get_active_wid() {
  if [[ "${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}" -ne 1 ]]; then
    return 0
  fi
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

get_pid_by_wid() {
  local wid="$1"
  get_wmctrl_lp | awk -v w="$wid" '$1==w {print $3; exit}'
}

get_cmdline_by_pid() {
  local pid="$1"
  [[ "${pid:-}" =~ ^[0-9]+$ ]] || return 1
  "$HOST_EXEC" "bash -lc 'tr \"\\0\" \" \" < /proc/${pid}/cmdline 2>/dev/null'" || true
}

cmdline_is_chrome() {
  local cmd="$1"
  [[ -n "${cmd:-}" ]] || return 1
  local cmd_lc
  cmd_lc="${cmd,,}"
  if [[ "$cmd_lc" == *"google-chrome"* ]] || [[ "$cmd_lc" == *"chromium"* ]] || [[ "$cmd_lc" == *"chrome/chrome"* ]]; then
    return 0
  fi
  return 1
}

cmdline_has_user_data_dir() {
  local cmd="$1"
  local dir="$2"
  [[ -n "${cmd:-}" ]] || return 1
  [[ -n "${dir:-}" ]] || return 1
  if [[ "${cmd}" == *"--user-data-dir=${dir}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${dir}"* ]]; then
    return 0
  fi
  return 1
}

cmdline_matches_profile() {
  local cmd="$1"
  if [[ "${PROFILE_LOCK}" -ne 1 ]]; then
    return 0
  fi
  [[ -n "${cmd:-}" ]] || return 1
  if [[ "${cmd}" == *"--user-data-dir=${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    return 0
  fi
  return 1
}

wm_command_matches_profile() {
  if [[ "${PROFILE_LOCK}" -ne 1 ]]; then
    return 0
  fi
  local wid="$1"
  local cmd
  cmd="$(get_wm_command_by_wid "$wid")"
  if [[ -z "${cmd:-}" ]]; then
    dbg "WM_COMMAND_MISSING wid=${wid}"
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir=${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    return 0
  fi
  if [[ "${cmd}" == *"--user-data-dir ${CHATGPT_CHROME_USER_DATA_DIR}"* ]]; then
    return 0
  fi
  return 1
}

log_profile_choice() {
  local wid="$1"
  local pid cmd cmd_ok
  if [[ "${PROFILE_LOCK}" -ne 1 ]]; then
    return 0
  fi
  pid="$(get_pid_by_wid "$wid")"
  cmd="$(get_cmdline_by_pid "$pid")"
  cmd_ok=0
  if cmdline_matches_profile "$cmd"; then
    cmd_ok=1
  fi
  dbg "WID_CHOSEN=${wid} PID=${pid} CMD_OK=${cmd_ok}"
}

wid_is_chrome() {
  local wid="$1"
  local pid cmd
  pid="$(get_pid_by_wid "$wid")"
  cmd="$(get_cmdline_by_pid "$pid")"
  if ! cmdline_is_chrome "$cmd"; then
    return 1
  fi
  if ! cmdline_matches_profile "$cmd"; then
    return 1
  fi
  if ! wm_command_matches_profile "$wid"; then
    return 1
  fi
  return 0
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
  while IFS=$'\t' read -r wid _pid title; do
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
  while IFS=$'\t' read -r wid _pid title; do
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
  local wid _pid title
  while IFS=$'\t' read -r wid _pid title; do
    [[ -z "${wid:-}" ]] && continue
    if grep -Fxq "${wid}" <<< "${before}"; then
      continue
    fi
    printf '%s\t%s\t%s\n' "$wid" "$_pid" "$title"
  done <<< "$candidates"
}

open_chatgpt_window() {
  if [[ ! -x "$CHROME_OPEN" ]]; then
    echo "ERROR: missing chatgpt_chrome_open.sh" >&2
    return 1
  fi
  CHATGPT_OPEN_URL="${CHATGPT_OPEN_URL}" \
    CHATGPT_CHROME_USER_DATA_DIR="${CHATGPT_CHROME_USER_DATA_DIR}" \
    CHATGPT_BRIDGE_CLASS="${CHATGPT_BRIDGE_CLASS}" \
    "$CHROME_OPEN" >/dev/null 2>&1 || true
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
    pin_reason=""
    pin_pid=""
    if wid_exists "$PIN_WID"; then
      pin_pid="$(get_pid_by_wid "$PIN_WID")"
      pin_cmd="$(get_cmdline_by_pid "$pin_pid")"
      TITLE_PIN="$(get_title_by_wid "$PIN_WID")"
      pin_ok=0
      case "${CHATGPT_TARGET}" in
        free)
          if cmdline_is_chrome "$pin_cmd" && cmdline_matches_profile "$pin_cmd" && \
             wm_command_matches_profile "$PIN_WID" && ! title_is_excluded "${TITLE_PIN:-}"; then
            pin_ok=1
          fi
          ;;
        paid)
          if cmdline_is_chrome "$pin_cmd" && \
             ! cmdline_has_user_data_dir "$pin_cmd" "$FREE_PROFILE_DIR" && \
             ! title_is_excluded "${TITLE_PIN:-}"; then
            pin_ok=1
          fi
          ;;
        dummy)
          if cmdline_is_chrome "$pin_cmd" && [[ "${TITLE_PIN:-}" == *"LUCY Dummy Chat"* ]]; then
            pin_ok=1
          fi
          ;;
      esac

      if [[ "${pin_ok}" -eq 1 ]]; then
        if [[ -z "${TITLE_PIN:-}" ]]; then
          TITLE_PIN="${TITLE_INCLUDE}"
        fi
        write_pin "$PIN_WID" "$TITLE_PIN"
        log_profile_choice "$PIN_WID"
        dbg "WID_CHOSEN=${PIN_WID} TITLE=${TITLE_PIN}"
        printf '%s\n' "$PIN_WID"
        exit 0
      fi
      if ! cmdline_is_chrome "$pin_cmd"; then
        pin_reason="NOT_CHROME"
      elif [[ "${CHATGPT_TARGET}" == "free" ]] && ! cmdline_matches_profile "$pin_cmd"; then
        pin_reason="PROFILE_MISMATCH"
      elif [[ "${CHATGPT_TARGET}" == "free" ]] && ! wm_command_matches_profile "$PIN_WID"; then
        pin_reason="WM_COMMAND_MISMATCH"
      elif [[ "${CHATGPT_TARGET}" == "paid" ]] && cmdline_has_user_data_dir "$pin_cmd" "$FREE_PROFILE_DIR"; then
        pin_reason="PROFILE_MISMATCH"
      elif title_is_excluded "${TITLE_PIN:-}"; then
        pin_reason="TITLE_EXCLUDED"
      else
        pin_reason="PIN_INVALID"
      fi
    else
      pin_reason="WID_MISSING"
    fi
    echo "PIN_INVALID=1 old_wid=${PIN_WID} reason=${pin_reason} pid=${pin_pid:-}" >&2
    if [[ "${CHATGPT_WID_PIN_ONLY:-0}" -eq 1 ]]; then
      echo "ERROR: PIN_INVALID WID=${PIN_WID}" >&2
      exit 3
    fi
    rm -f "$PIN_FILE" 2>/dev/null || true
    PIN_RECOVER_NEEDS_WRITE=1
  fi
fi

if [[ "${CHATGPT_WID_PIN_ONLY:-0}" -eq 1 ]] && [[ ! -f "${PIN_FILE}" ]]; then
  echo "ERROR: PIN_ONLY requires existing pin file (${PIN_FILE})" >&2
  exit 3
fi

if [[ "${PIN_RECOVER_NEEDS_WRITE}" -eq 1 ]]; then
  if [[ "${CHATGPT_TARGET}" == "free" ]]; then
    STRONG_CANDIDATES="$(list_strong_candidates)"
  elif [[ "${CHATGPT_TARGET}" == "paid" ]]; then
    STRONG_CANDIDATES="$(list_paid_candidates)"
  else
    STRONG_CANDIDATES="$(list_dummy_candidates)"
  fi
  strong_count="$(printf '%s\n' "$STRONG_CANDIDATES" | awk 'NF{c++} END{print c+0}')"
  RECOVER_WID=""
  if [[ "${strong_count}" -ge 1 ]]; then
    if [[ "${strong_count}" -eq 1 ]]; then
      strong_line="$(printf '%s\n' "$STRONG_CANDIDATES" | head -n 1)"
      RECOVER_WID="$(cut -f1 <<< "$strong_line")"
    else
      RECOVER_WID="$(choose_latest_wid "$STRONG_CANDIDATES")"
    fi
  else
    if [[ "${CHATGPT_TARGET}" == "paid" ]] || [[ "${CHATGPT_TARGET}" == "dummy" ]]; then
      if [[ "${CHATGPT_TARGET}" == "paid" ]] && [[ -x "$PAID_ENSURE" ]]; then
        if "$PAID_ENSURE" >/dev/null 2>&1; then
          STRONG_CANDIDATES="$(list_paid_candidates)"
          RECOVER_WID="$(choose_latest_wid "$STRONG_CANDIDATES")"
        fi
      fi
      if [[ -z "${RECOVER_WID:-}" ]]; then
        echo "ERROR: PIN_INVALID and no candidates for target=${CHATGPT_TARGET}" >&2
        exit 3
      fi
    fi
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
  log_profile_choice "$RECOVER_WID"
  echo "PIN_RECOVERED=1 new_wid=${RECOVER_WID}" >&2
  printf '%s\n' "$RECOVER_WID"
  exit 0
fi

# 1) Selección normal
if [[ "${CHATGPT_TARGET}" == "free" ]]; then
  CANDIDATES="$(list_chrome_candidates)"
elif [[ "${CHATGPT_TARGET}" == "paid" ]]; then
  CANDIDATES="$(list_paid_candidates)"
else
  CANDIDATES="$(list_dummy_candidates)"
fi
WID="$(choose_wid "$CANDIDATES" "$(get_active_wid)")"
if [[ -n "${WID:-}" ]]; then
  log_profile_choice "$WID"
fi

# 2) Si no hay ventana Chrome, abrir ChatGPT y esperar (si no está deshabilitado)
if [[ -z "${WID:-}" ]]; then
  if [[ "${CHATGPT_TARGET}" == "paid" ]]; then
    if [[ -x "$PAID_ENSURE" ]]; then
      "$PAID_ENSURE" >/dev/null 2>&1 || true
      CANDIDATES="$(list_paid_candidates)"
      WID="$(choose_wid "$CANDIDATES" "$(get_active_wid)")"
      [[ -n "${WID:-}" ]] && log_profile_choice "$WID"
    fi
    if [[ -z "${WID:-}" ]]; then
      echo "ERROR: NO_CANDIDATE_WID target=${CHATGPT_TARGET}" >&2
      exit 3
    fi
  elif [[ "${CHATGPT_TARGET}" == "dummy" ]]; then
    echo "ERROR: NO_CANDIDATE_WID target=${CHATGPT_TARGET}" >&2
    exit 3
  else
    if [[ "${CHATGPT_GET_WID_NOOPEN:-0}" -eq 1 ]]; then
      echo "ERROR: NO_CANDIDATE_WID" >&2
      exit 3
    fi
    WID="$(open_chatgpt_and_pick_new || true)"
    if [[ -n "${WID:-}" ]]; then
      log_profile_choice "$WID"
    fi
  fi
fi

if [[ -z "${WID:-}" ]]; then
  if [[ "${PROFILE_LOCK}" -eq 1 ]]; then
    echo "ERROR: no encuentro ventana ChatGPT en el perfil ${CHATGPT_CHROME_USER_DATA_DIR}. Abrí ChatGPT y reintentá." >&2
  else
    echo "ERROR: no encuentro ventana ChatGPT en Chrome. Abrí ChatGPT y reintentá." >&2
  fi
  exit 3
fi

printf '%s\n' "$WID"

# A24_DISABLE_ACTIVE_WINDOW_FALLBACK
# Si se pidió explícitamente NO usar ventana activa, forzamos fallo en ese camino.
# (Los callers en modo diego hacen repin por launch.)
if [[ "${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}" == "0" ]]; then
  export CHATGPT_DISABLE_ACTIVE_WINDOW=1
fi
