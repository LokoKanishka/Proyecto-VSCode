#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
HOST_EXEC="$ROOT/scripts/x11_host_exec.sh"

use_host=0
if [[ "${LUCY_FORCE_HOST_DOCKER:-0}" == "1" ]]; then
  use_host=1
elif command -v docker >/dev/null 2>&1; then
  if ! docker info >/dev/null 2>&1; then
    use_host=1
  fi
else
  use_host=1
fi

if [[ "${use_host}" -eq 0 ]]; then
  docker "$@"
  exit $?
fi

cmd="docker"
for arg in "$@"; do
  cmd+=" $(printf '%q' "$arg")"
done

"$HOST_EXEC" "bash -lc '${cmd}'"
