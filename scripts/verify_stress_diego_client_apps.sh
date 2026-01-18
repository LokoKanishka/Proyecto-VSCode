#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -r "$ROOT/scripts/x11_env.sh" ]; then
  # shellcheck source=/dev/null
  . "$ROOT/scripts/x11_env.sh"
fi

GUARD="$ROOT/scripts/chrome_guard_diego_client.sh"
ENSURE="$ROOT/scripts/chrome_ensure_url_in_window.sh"
CAPTURE="$ROOT/scripts/chrome_capture_active_tab.sh"

N_CG="${1:-10}"
N_YT="${2:-10}"

PROFILE_NAME="${CHROME_PROFILE_NAME:-diego}"
DIEGO_EMAIL="${CHROME_DIEGO_EMAIL:-chatjepetex2025@gmail.com}"

CHATGPT_URL="${CHATGPT_STRESS_URL:-https://chatgpt.com/}"
YOUTUBE_URL="${YOUTUBE_STRESS_URL:-https://www.youtube.com/}"

OUT="/tmp/lucy_stress_diego_client_apps_$(date +%Y%m%d_%H%M%S)_$$"
mkdir -p "$OUT"
echo "OUTDIR=$OUT"

_need() { command -v "$1" >/dev/null 2>&1 || { echo "MISSING_DEP: $1" >&2; exit 2; }; }
_need xdotool
_need wmctrl

if [ ! -x "$GUARD" ]; then echo "ERROR_NO_GUARD: $GUARD" >&2; exit 2; fi
if [ ! -x "$ENSURE" ]; then echo "ERROR_NO_ENSURE: $ENSURE" >&2; exit 2; fi
if [ ! -x "$CAPTURE" ]; then echo "ERROR_NO_CAPTURE: $CAPTURE" >&2; exit 2; fi

_host_lc() {
  # input: URL
  printf '%s' "$1" | tr '[:upper:]' '[:lower:]' | sed -E 's#^[a-z]+://([^/]+).*#\1#' | sed 's/:.*//'
}

_check_active_window_is() {
  local wid_hex="$1"
  local wid_dec=$((wid_hex))
  local act
  act="$(xdotool getactivewindow 2>/dev/null || true)"
  if [ -n "$act" ] && [ "$act" -ne "$wid_dec" ]; then
    echo "WARN_ACTIVE_WINDOW_CHANGED act_dec=$act expected_dec=$wid_dec" >&2
  fi
}

_run_one() {
  local label="$1"
  local url="$2"
  local iter="$3"
  local iter_dir="$OUT/$label/iter_$(printf '%02d' "$iter")"
  mkdir -p "$iter_dir"

  # 1) Guard: SIEMPRE fuerza/valida cliente Diego por EMAIL y devuelve WID
  set +e
  guard_out="$(CHROME_PROFILE_NAME="$PROFILE_NAME" CHROME_DIEGO_EMAIL="$DIEGO_EMAIL" "$GUARD" "https://www.google.com/" 2>&1)"
  guard_rc=$?
  set -e
  printf '%s\n' "$guard_out" >"$iter_dir/guard.txt"
  if [ "$guard_rc" -ne 0 ]; then
    echo "FAIL_GUARD rc=$guard_rc iter=$iter (see $iter_dir/guard.txt)" >&2
    exit 3
  fi

  wid_hex="$(printf '%s\n' "$guard_out" | awk -F= '/^WID_HEX=/{print $2}' | tail -n 1)"
  email="$(printf '%s\n' "$guard_out" | awk -F= '/^EMAIL=/{print $2}' | tail -n 1)"
  if [ -z "${wid_hex:-}" ]; then
    echo "FAIL_NO_WID iter=$iter (see $iter_dir/guard.txt)" >&2
    exit 3
  fi
  if [ "${email:-}" != "$DIEGO_EMAIL" ]; then
    echo "FAIL_EMAIL_MISMATCH iter=$iter got=${email:-<empty>} expected=$DIEGO_EMAIL" >&2
    exit 3
  fi

  # 2) URL-lock dentro de ESA MISMA ventana (sin abrir otro Chrome)
  set +e
  ensure_out="$("$ENSURE" "$wid_hex" "$url" 10 2>&1)"
  ensure_rc=$?
  set -e
  printf '%s\n' "$ensure_out" >"$iter_dir/ensure.txt"
  if [ "$ensure_rc" -ne 0 ]; then
    echo "FAIL_ENSURE_URL rc=$ensure_rc iter=$iter (see $iter_dir/ensure.txt)" >&2
    exit 3
  fi

  _check_active_window_is "$wid_hex"

  # 3) Capture + validación de host
  mkdir -p "$iter_dir/capture"
  set +e
  cap_out="$("$CAPTURE" "$wid_hex" "$iter_dir/capture" 2>&1)"
  cap_rc=$?
  set -e
  printf '%s\n' "$cap_out" >"$iter_dir/capture/capture.txt"
  if [ "$cap_rc" -ne 0 ]; then
    echo "FAIL_CAPTURE rc=$cap_rc iter=$iter (see $iter_dir/capture/capture.txt)" >&2
    exit 3
  fi

  cap_url="$(cat "$iter_dir/capture/url.txt" 2>/dev/null || true)"
  cap_title="$(cat "$iter_dir/capture/title.txt" 2>/dev/null || true)"
  host="$(_host_lc "$cap_url")"

  case "$label" in
    chatgpt)
      if [ "$host" != "chatgpt.com" ] && [ "$host" != "chat.openai.com" ]; then
        echo "FAIL_BAD_HOST_CHATGPT iter=$iter host=$host url=$cap_url title=$cap_title" >&2
        exit 3
      fi
      ;;
    youtube)
      case "$host" in
        youtube.com|www.youtube.com|m.youtube.com|youtu.be) : ;;
        *)
          echo "FAIL_BAD_HOST_YOUTUBE iter=$iter host=$host url=$cap_url title=$cap_title" >&2
          exit 3
          ;;
      esac
      ;;
  esac

  echo "OK: $label iter=$iter wid=$wid_hex email=$email host=$host"
}

echo "== STRESS_CHATGPT n=$N_CG ==" | tee "$OUT/summary.txt"
for i in $(seq 1 "$N_CG"); do
  _run_one "chatgpt" "$CHATGPT_URL" "$i" | tee -a "$OUT/summary.txt"
done

echo "== STRESS_YOUTUBE n=$N_YT ==" | tee -a "$OUT/summary.txt"
for i in $(seq 1 "$N_YT"); do
  _run_one "youtube" "$YOUTUBE_URL" "$i" | tee -a "$OUT/summary.txt"
done

echo "OK_STRESS_DIEGO_CLIENT_APPS chatgpt=$N_CG youtube=$N_YT outdir=$OUT" | tee -a "$OUT/summary.txt"
