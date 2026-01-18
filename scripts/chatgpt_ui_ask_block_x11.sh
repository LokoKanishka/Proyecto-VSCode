#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
# --- Diego client guard ---
export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
export CHROME_PROFILE_NAME="${CHROME_PROFILE_NAME:-${CHATGPT_PROFILE_NAME}}"
export CHROME_DIEGO_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"
export CHROME_DIEGO_PIN_FILE="${CHROME_DIEGO_PIN_FILE:-$ROOT/diagnostics/pins/chrome_diego.wid}"

pre="$("$ROOT/scripts/chatgpt_diego_preflight.sh")"
CHROME_WID_HEX="$(printf '%s\n' "$pre" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
if [ -z "${CHROME_WID_HEX:-}" ]; then
  echo "ERROR_DIEGO_PREFLIGHT_NO_WID" >&2
  exit 3
fi
export CHATGPT_WID_HEX="$CHROME_WID_HEX"
export CHATGPT_WID_PIN_FILE="$CHROME_DIEGO_PIN_FILE"
export CHATGPT_ALLOW_ACTIVE_WINDOW=0
export CHATGPT_WID_PIN_ONLY=1
# --- end Diego client guard ---


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DIR="$SCRIPT_DIR"
RESOLVE_BY_URL="$DIR/chatgpt_resolve_wid_by_url.sh"

if [ -r "$DIR/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$DIR/x11_env.sh"
fi

if [ -x "$DIR/x11_require_access.sh" ]; then
  "$DIR/x11_require_access.sh"
fi

# Auto-detect/ensure ChatGPT window id if not provided (VENTANA PUENTE)
if [ -z "${CHATGPT_WID_HEX:-}" ]; then
  if [[ "${CHATGPT_TARGET:-paid}" == "paid" ]]; then
    export CHATGPT_ALLOW_ACTIVE_WINDOW="${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}"
    export CHATGPT_WID_PIN_ONLY="${CHATGPT_WID_PIN_ONLY:-1}"
    export CHATGPT_PROFILE_NAME="${CHATGPT_PROFILE_NAME:-diego}"
    if [[ -z "${CHATGPT_WID_PIN_FILE:-}" ]]; then
      export CHATGPT_WID_PIN_FILE="$REPO_ROOT/diagnostics/pins/chatgpt_diego.wid"
    fi
    mkdir -p "$(dirname "$CHATGPT_WID_PIN_FILE")" 2>/dev/null || true
    if [[ ! -s "${CHATGPT_WID_PIN_FILE:-}" ]]; then
      set +e
      CHATGPT_WID_PIN_FILE="$CHATGPT_WID_PIN_FILE" "$RESOLVE_BY_URL" 12 9 >/dev/null 2>&1
      resolve_rc=$?
      set -e
      if [[ "$resolve_rc" -ne 0 ]]; then
        echo "ERROR: paid resolve by URL failed (rc=$resolve_rc)" >&2
        exit 3
      fi
    fi
  fi
  if [ -x "$DIR/chatgpt_bridge_ensure.sh" ]; then
    CHATGPT_WID_HEX="$("$DIR/chatgpt_bridge_ensure.sh")"
  elif [ -x "$DIR/chatgpt_get_wid.sh" ]; then
    CHATGPT_WID_HEX="$("$DIR/chatgpt_get_wid.sh" || true)"
  fi
  export CHATGPT_WID_HEX
fi

QUESTION="${1:-}"
if [ -z "$QUESTION" ]; then
  echo "USO: CHATGPT_WID_HEX=0x... $0 \"pregunta\"" >&2
  exit 2
fi

[ -n "${CHATGPT_WID_HEX:-}" ] || { echo "ERROR: no hay CHATGPT_WID_HEX"; exit 2; }

TOKEN="$(date +%s)_$RANDOM"
ACTIVE_WID=""
if [[ "${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}" -eq 1 ]]; then
  ACTIVE_WID="$(xdotool getactivewindow 2>/dev/null || true)"
fi

START="LUCY_BLOCK_${TOKEN}:"
END="LUCY_END_${TOKEN}"

PROMPT="LUCY_REQ_${TOKEN}: ${QUESTION}

Respondé SOLO con este bloque multilínea, sin texto fuera del bloque.
Entre las dos marcas poné el contenido:

${START}
${END}"

CHATGPT_WID_HEX="$CHATGPT_WID_HEX" "${REPO_ROOT}/scripts/chatgpt_focus_paste.sh" "$PROMPT" >/dev/null
xdotool key --window "$((CHATGPT_WID_HEX))" Return

if [ -n "${ACTIVE_WID:-}" ]; then
  xdotool windowactivate "$ACTIVE_WID" >/dev/null 2>&1 || true
fi

ASK_TIMEOUT="${ASK_TIMEOUT:-120}"
deadline=$((SECONDS+ASK_TIMEOUT))

while [ $SECONDS -lt $deadline ]; do
  ACTIVE_LOOP_WID=""
  if [[ "${CHATGPT_ALLOW_ACTIVE_WINDOW:-0}" -eq 1 ]]; then
    ACTIVE_LOOP_WID="$(xdotool getactivewindow 2>/dev/null || true)"
  fi
  text="$(CHATGPT_WID_HEX="$CHATGPT_WID_HEX" "${REPO_ROOT}/scripts/chatgpt_copy_chat_text.sh" 2>/dev/null || true)"
  if [ -n "${ACTIVE_LOOP_WID:-}" ]; then
    xdotool windowactivate "$ACTIVE_LOOP_WID" >/dev/null 2>&1 || true
  fi

  if printf '%s\n' "$text" | grep -qE "^${START}$" && printf '%s\n' "$text" | grep -qE "^${END}$"; then
    out="$(printf '%s
' "$text" | awk -v s="$START" -v e="$END" '
      $0==s {inside=1; buf=""; next}
      inside && $0==e {last=buf; inside=0; next}
      inside {buf = buf $0 ORS}
      END {printf "%s", last}
    ')"
    if [ -n "${out:-}" ]; then
      printf '%s\n' "$out"
      exit 0
    fi
  fi

  sleep 2
done

echo "ERROR: timeout esperando bloque ${START} ... ${END}" >&2
exit 1
