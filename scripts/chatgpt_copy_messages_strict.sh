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
  echo "ERROR_NO_WID" >&2
  exit 3
fi

WID_DEC="$(printf "%d" "$WID_HEX" 2>/dev/null || echo 0)"
if [[ "${WID_DEC}" -le 0 ]]; then
  echo "ERROR_INVALID_WID" >&2
  exit 3
fi

geo="$("$HOST_EXEC" "xdotool getwindowgeometry --shell ${WID_DEC}" 2>/dev/null || true)"
eval "$geo" || true
: "${WIDTH:=1200}"
: "${HEIGHT:=900}"

# Coordinates to try: (X%, Y%)
# 1. Slightly right-center (avoid sidebar)
# 2. Lower right
# 3. Center
ATTEMPTS=( "60 60" "70 70" "50 50" )

# Strings that indicate we copied the sidebar
SIDEBAR_PATTERNS=( "Historial" "Nuevo chat" "ChatGPT Plus" "Upgrade plan" )

for attempt in "${ATTEMPTS[@]}"; do
  read -r x_pct y_pct <<< "$attempt"
  
  px=$(( WIDTH * x_pct / 100 ))
  py=$(( HEIGHT * y_pct / 100 ))
  
  # Jitter
  jitter=$(( (RANDOM % 5) - 2 ))
  px=$(( px + jitter ))
  py=$(( py + jitter ))
  
  cmd="PX='${px}' PY='${py}' WID_HEX='${WID_HEX}' WID_DEC='${WID_DEC}'; "
  cmd+="set -euo pipefail; "
  cmd+="wmctrl -ia \"\$WID_HEX\" 2>/dev/null || true; "
  cmd+="xdotool windowactivate --sync \"\$WID_DEC\" 2>/dev/null || true; "
  cmd+="xdotool key --clearmodifiers End 2>/dev/null || true; " # Force scroll bottom
  cmd+="sleep 0.2; "
  cmd+="xdotool mousemove --window \"\$WID_DEC\" \"\$PX\" \"\$PY\" click 1 2>/dev/null || true; "
  cmd+="sleep 0.15; "
  cmd+="xdotool key --clearmodifiers ctrl+a 2>/dev/null || true; "
  cmd+="sleep 0.15; "
  cmd+="xdotool key --clearmodifiers ctrl+c 2>/dev/null || true; "
  cmd+="sleep 0.25; "
  # Read clipboard loop
  cmd+="t=''; "
  cmd+="for i in \$(seq 1 10); do "
  cmd+="  t=\$(timeout 0.5s xclip -selection clipboard -o 2>/dev/null || true); "
  cmd+="  [[ -n \"\$t\" ]] && break; "
  cmd+="  t=\$(timeout 0.5s xsel --clipboard --output 2>/dev/null || true); "
  cmd+="  [[ -n \"\$t\" ]] && break; "
  cmd+="  sleep 0.1; "
  cmd+="done; "
  cmd+="printf '%s' \"\$t\""

  # Execute
  clipboard_content="$("$HOST_EXEC" "$cmd")"
  
  # Validate
  is_bad=0
  if [[ ${#clipboard_content} -lt 10 ]]; then
    is_bad=1
  else
    for pattern in "${SIDEBAR_PATTERNS[@]}"; do
      if [[ "$clipboard_content" == *"$pattern"* ]]; then
        is_bad=1
        break
      fi
    done
  fi
  
  if [[ "$is_bad" -eq 0 ]]; then
    echo "__LUCY_COPY_META__ OK attempts=${attempt}" >&2
    printf '%s' "$clipboard_content"
    exit 0
  fi
  
  echo "WARN: strict copy attempt failed (sidebar/empty) at ${x_pct}%,${y_pct}%" >&2
done

echo "ERROR: strict copy failed after all attempts" >&2
exit 1
