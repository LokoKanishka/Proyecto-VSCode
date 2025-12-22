#!/usr/bin/env bash
set -euo pipefail

LOG="${1:-}"
if [[ -z "${LOG}" ]]; then
  LOG="$(ls -1t logs/voice_*.log | head -n 1)"
fi

if [[ ! -f "${LOG}" ]]; then
  echo "ERROR: no existe el log: ${LOG}" >&2
  exit 1
fi

OUT="tests/fixtures/utterances_search.txt"
TMP="$(mktemp)"

extract() {
  # Ej: [LucyVoice] STT text: 'Lucy dormí. Lucy dormí.'
  grep -oP "\\[LucyVoice\\] STT text: '\\K[^']+" "${LOG}" \
    | sed 's/[[:space:]]\+/ /g; s/^ *//; s/ *$//' \
    | awk 'NF'
}

{
  [[ -f "${OUT}" ]] && cat "${OUT}"
  extract
} | awk '!seen[$0]++' > "${TMP}"

mv "${TMP}" "${OUT}"

echo "[extract] Log: ${LOG}"
echo "[extract] Output: ${OUT}"
echo "[extract] Lines: $(wc -l < "${OUT}")"
echo "[extract] Tail:"
tail -n 20 "${OUT}" || true
