#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
FILE_CALL="$ROOT/scripts/x11_file_call.sh"

# Ejecuta un comando en el host vía file-agent y devuelve SOLO el stdout del comando.
# Propaga el exit code real (RC=...).
if [[ $# -eq 0 ]]; then
  echo "usage: x11_host_exec.sh <command...>" 1>&2
  exit 2
fi

# Construir comando: si te pasan 1 arg, lo tomamos tal cual (permite pipes/redirecciones).
# Si te pasan varios args, los quoteamos.
cmd=""
if [[ $# -eq 1 ]]; then
  cmd="$1"
else
  for a in "$@"; do
    cmd+=" $(printf '%q' "$a")"
  done
fi

out="$("$FILE_CALL" "bash -lc $(printf '%q' "$cmd")")"
rc="$(printf '%s\n' "$out" | head -n 1 | sed 's/^RC=//')"
printf '%s\n' "$out" | tail -n +2
exit "${rc:-0}"
