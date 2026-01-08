#!/usr/bin/env bash
set -euo pipefail

DRYRUN="${LUCY_GC_DRYRUN:-}"
BRIDGE_DIR="/tmp/lucy_chatgpt_bridge"
ASK_GLOB="lucy_chatgpt_ask_run_*"
KEEP_DAYS="${KEEP_DAYS:-${LUCY_GC_BRIDGE_DAYS:-3}}"
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

if [[ -z "${DRYRUN}" ]]; then
  DRYRUN=1
fi

log "LUCY_TMP_GC_START dryrun=${DRYRUN} keep_days=${KEEP_DAYS}"

if [[ -d "${BRIDGE_DIR}" ]]; then
  today="$(date +%F)"
  today_epoch="$(date -d "${today}" +%s)"
  while IFS= read -r -d '' d; do
    base="$(basename "$d")"
    if [[ "${base}" == "${today}" ]]; then
      log "KEEP_TODAY ${d}"
      continue
    fi
    if [[ ! "${base}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]]; then
      log "SKIP_NON_DATE ${d}"
      continue
    fi
    dir_epoch="$(date -d "${base}" +%s 2>/dev/null || true)"
    if [[ -z "${dir_epoch}" ]]; then
      log "SKIP_BAD_DATE ${d}"
      continue
    fi
    age_days=$(( (today_epoch - dir_epoch) / 86400 ))
    if (( age_days > KEEP_DAYS )); then
      rm_path "$d"
    else
      log "KEEP_RECENT ${d} age_days=${age_days}"
    fi
  done < <(find "${BRIDGE_DIR}" -mindepth 1 -maxdepth 1 -type d -print0)
else
  log "INFO: ${BRIDGE_DIR} no existe"
fi

while IFS= read -r -d '' p; do
  rm_path "$p"
done < <(find /tmp -maxdepth 1 -name "${ASK_GLOB}" -mtime "+${ASK_DAYS}" -print0)

log "LUCY_TMP_GC_DONE"
