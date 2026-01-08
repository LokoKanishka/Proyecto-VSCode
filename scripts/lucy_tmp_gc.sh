#!/usr/bin/env bash
set -euo pipefail

DRYRUN="${LUCY_GC_DRYRUN:-0}"
BRIDGE_DIR="/tmp/lucy_chatgpt_bridge"
ASK_GLOB="lucy_chatgpt_ask_run_*"
BRIDGE_DAYS="${LUCY_GC_BRIDGE_DAYS:-7}"
ASK_DAYS="${LUCY_GC_ASK_DAYS:-3}"

log() {
  printf '%s\n' "$*"
}

rm_path() {
  local path="$1"
  if [[ "${DRYRUN}" == "1" ]]; then
    log "DRYRUN: rm -rf ${path}"
  else
    rm -rf "${path}"
    log "REMOVED=${path}"
  fi
}

log "LUCY_TMP_GC_START dryrun=${DRYRUN}"

if [[ -d "${BRIDGE_DIR}" ]]; then
  while IFS= read -r -d '' d; do
    rm_path "$d"
  done < <(find "${BRIDGE_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime "+${BRIDGE_DAYS}" -print0)
else
  log "INFO: ${BRIDGE_DIR} no existe"
fi

while IFS= read -r -d '' p; do
  rm_path "$p"
done < <(find /tmp -maxdepth 1 -name "${ASK_GLOB}" -mtime "+${ASK_DAYS}" -print0)

log "LUCY_TMP_GC_DONE"
