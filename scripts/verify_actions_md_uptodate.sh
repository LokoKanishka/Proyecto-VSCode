#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

cp "${ROOT}/docs/ACTIONS.md" /tmp/ACTIONS.md.before
"${ROOT}/scripts/gen_actions_md.sh" >/tmp/gen_actions_md.out

if ! diff -u /tmp/ACTIONS.md.before "${ROOT}/docs/ACTIONS.md"; then
  echo "ERROR: ACTIONS.md out of date" >&2
  exit 1
fi

echo "VERIFY_ACTIONS_MD_UPTODATE_OK"
