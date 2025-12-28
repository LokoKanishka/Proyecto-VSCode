#!/usr/bin/env bash
set -euo pipefail

# Devuelve el WID de la ventana "bridge" de ChatGPT, identificándola por el perfil separado.
# Requiere: wmctrl, xprop (via wrappers x11_wrap si estás en sandbox)

PROFILE_DIR="${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chatgpt_bridge_profile}"

pid_from_wid() {
  local wid="$1"
  xprop -id "$wid" _NET_WM_PID 2>/dev/null     | awk -F' = ' '{print $2}'     | tr -d ' ' || true
}

cmdline_from_pid() {
  local pid="$1"
  tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true
}

is_bridge_wid() {
  local wid="$1"
  local pid cmd
  pid="$(pid_from_wid "$wid")"
  [[ -n "${pid:-}" ]] || return 1
  cmd="$(cmdline_from_pid "$pid")"
  [[ -n "${cmd:-}" ]] || return 1
  # match flexible: que aparezca el path del perfil
  echo "$cmd" | grep -Fq "$PROFILE_DIR"
}

active_window() {
  xprop -root _NET_ACTIVE_WINDOW 2>/dev/null     | awk '{print $NF}'     | sed 's/[^0-9a-fx]//g' || true
}

main() {
  local wids=() wid act
  # candidatos: todas las ventanas chrome/chromium
  while read -r wid; do
    [[ -n "$wid" ]] || continue
    if is_bridge_wid "$wid"; then
      wids+=("$wid")
    fi
  done < <(wmctrl -lx | awk 'tolower($3) ~ /(google-chrome|chromium)/ {print $1}')

  if [[ "${#wids[@]}" -eq 0 ]]; then
    echo "ERROR: no se encontró ventana bridge (perfil: $PROFILE_DIR)" 1>&2
    exit 1
  fi

  act="$(active_window)"
  if [[ -n "${act:-}" ]]; then
    for wid in "${wids[@]}"; do
      if [[ "$wid" == "$act" ]]; then
        echo "$wid"
        exit 0
      fi
    done
  fi

  # fallback: primera encontrada
  echo "${wids[0]}"
}

main "$@"
