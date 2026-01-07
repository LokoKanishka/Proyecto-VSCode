#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

prompt="Respondé exactamente con: OK"

for i in 1 2 3; do
  tmp_err="$(mktemp)"
  set +e
  out="$(python3 -m lucy_agents.chatgpt_bridge "${prompt}" 2> >(tee "${tmp_err}" >&2))"
  rc=$?
  set -e

  if [[ "${rc}" -ne 0 ]]; then
    echo "ERROR: ask ${i} failed (rc=${rc})" >&2
    exit 1
  fi

  if [[ "${out}" != "OK" ]]; then
    echo "ERROR: ask ${i} returned unexpected output: '${out}'" >&2
    exit 1
  fi

  echo "${out}"
  rm -f "${tmp_err}"
 done

echo "VERIFY_CHATGPT_BRIDGE_PY_OK"
