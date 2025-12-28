#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

export X11_FILE_IPC_DIR="${X11_FILE_IPC_DIR:-$ROOT/diagnostics/x11_file_ipc}"
source "$ROOT/scripts/x11_env.sh" || true
export CHATGPT_BRIDGE_PROFILE_DIR="${CHATGPT_BRIDGE_PROFILE_DIR:-$HOME/.cache/lucy_chatgpt_bridge_profile}"

N="${1:-10}"
PROMPT="${2:-Respondé exactamente con: OK}"

RUN_ID="$(date +%s)"
LOG="/tmp/lucy_ask_loop_${RUN_ID}.tsv"
echo -e "i\trc\tms\tok\tout_head" >"$LOG"

# asegurar bridge una vez
timeout 8s "$ROOT/scripts/chatgpt_bridge_ensure.sh" >/dev/null 2>&1 || true

ok_count=0
fail_count=0

for i in $(seq 1 "$N"); do
  start_ms="$(date +%s%3N)"
  set +e
  out="$("$ROOT/scripts/lucy_ask_safe.sh" "$PROMPT")"
  rc=$?
  set -e
  end_ms="$(date +%s%3N)"
  dur_ms=$((end_ms - start_ms))

  # normaliza head para log
  out_one="$(printf '%s' "$out" | tr -d '\r' | head -n 1)"
  out_head="$(printf '%s' "$out_one" | head -c 90)"

  if printf '%s\n' "$out_one" | grep -Eq '^LUCY_ANSWER_[0-9_]+: OK$'; then
    ok=1
    ok_count=$((ok_count+1))
  else
    ok=0
    fail_count=$((fail_count+1))
  fi

  echo -e "${i}\t${rc}\t${dur_ms}\t${ok}\t${out_head}" >>"$LOG"
  printf "ITER %02d/%02d rc=%s ms=%s ok=%s\n" "$i" "$N" "$rc" "$dur_ms" "$ok"
done

python3 - <<PY
import csv, statistics
path = "$LOG"
rows=[]
with open(path, newline='', encoding="utf-8") as f:
    r=csv.DictReader(f, delimiter="\t")
    for row in r:
        row["rc"]=int(row["rc"])
        row["ms"]=int(row["ms"])
        row["ok"]=int(row["ok"])
        rows.append(row)

ms=[x["ms"] for x in rows]
oks=sum(x["ok"] for x in rows)
fails=len(rows)-oks
print()
print("LOG=", path)
print("N=", len(rows), "OK=", oks, "FAIL=", fails)
print("ms_min=", min(ms), "ms_p50=", int(statistics.median(ms)), "ms_avg=", int(sum(ms)/len(ms)), "ms_max=", max(ms))
bad=[x for x in rows if x["ok"]==0]
if bad:
    print("\nFAIL_SAMPLES (hasta 5):")
    for x in bad[:5]:
        print(f"  i={x['i']} rc={x['rc']} ms={x['ms']} out_head={x['out_head']!r}")
PY
