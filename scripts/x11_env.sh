#!/usr/bin/env bash

# Best-effort X11 env setup for scripts that call xdotool/wmctrl/xclip.
if [ -n "${_X11_ENV_LOADED:-}" ]; then
  return 0
fi
_X11_ENV_LOADED=1

_x11_uid="${UID:-}"
if [ -z "${_x11_uid}" ]; then
  _x11_uid="$(id -u 2>/dev/null || true)"
fi

if [ -z "${DISPLAY:-}" ]; then
  sock="$(ls -1 /tmp/.X11-unix/X* 2>/dev/null | sort | head -n 1 || true)"
  if [ -n "${sock:-}" ]; then
    num="${sock##*/X}"
    num="${num%%.*}"
    DISPLAY=":${num}"
    export DISPLAY
  fi
fi

if [ -z "${XAUTHORITY:-}" ] || [ ! -r "${XAUTHORITY:-}" ]; then
  cand="$(ps -eo args 2>/dev/null | awk '
    /[X]org|[X]wayland/ {
      for (i=1; i<=NF; i++) if ($i == "-auth" && (i+1)<=NF) { print $(i+1); exit }
    }' || true)"
  if [ -n "${cand:-}" ] && [ -r "$cand" ]; then
    XAUTHORITY="$cand"
    export XAUTHORITY
  fi
fi

if [ -z "${XAUTHORITY:-}" ] || [ ! -r "${XAUTHORITY:-}" ]; then
  if [ -n "${HOME:-}" ] && [ -r "$HOME/.Xauthority" ]; then
    export XAUTHORITY="$HOME/.Xauthority"
  elif [ -n "${_x11_uid:-}" ] && [ -r "/run/user/${_x11_uid}/gdm/Xauthority" ]; then
    export XAUTHORITY="/run/user/${_x11_uid}/gdm/Xauthority"
  elif [ -n "${_x11_uid:-}" ]; then
    cand="$(ls -1 "/run/user/${_x11_uid}"/.mutter-Xwaylandauth.* 2>/dev/null | head -n 1 || true)"
    if [ -n "${cand:-}" ] && [ -r "$cand" ]; then
      export XAUTHORITY="$cand"
    fi
  fi
fi
