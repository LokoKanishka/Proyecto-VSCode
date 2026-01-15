#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
GET_URL="$ROOT/scripts/chatgpt_get_url_x11.sh"

TARGET="${CHATGPT_TARGET:-free}"
OUT="$ROOT/diagnostics/chatgpt_thread_url_${TARGET}.txt"

url="$("$GET_URL" 2>/dev/null || true)"
if [[ -z "${url:-}" ]]; then
  echo "ERROR: no pude leer URL (¿ventana ChatGPT activa?)" >&2
  exit 4
fi
if [[ "$url" != *"/c/"* ]]; then
  echo "ERROR_NOT_IN_THREAD: URL=$url (abrí el hilo /c/ y reintentá)" >&2
  exit 8
fi

printf '%s\n' "$url" > "$OUT"
echo "OK: pinned THREAD_URL en $OUT"
