#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

prompt="$*"
if [[ -z "${prompt}" ]]; then
  echo "ERROR: missing prompt" >&2
  exit 1
fi

cd "${ROOT}"
exec python3 -m lucy_agents.chatgpt_client "${prompt}"
