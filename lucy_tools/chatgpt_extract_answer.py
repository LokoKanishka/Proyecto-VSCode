#!/usr/bin/env python3
import re, sys

if len(sys.argv) != 2:
    print("USO: chatgpt_extract_answer.py LUCY_ANSWER_xxx", file=sys.stderr)
    sys.exit(2)

label = sys.argv[1].strip()
pat = re.compile(rf"^\s*{re.escape(label)}\s*:\s*(.*)\s*$")

lines = sys.stdin.read().splitlines()
best = None

for ln in lines:
    m = pat.match(ln)
    if not m:
        continue
    val = (m.group(1) or "").strip()
    low = val.lower()

    # descartar placeholders del prompt
    if not val:
        continue
    if (
        val.startswith("<")
        or "tu respuesta" in low
        or "una sola línea" in low
        or "una sola linea" in low
    ):
        continue

    best = f"{label}: {val}"

if best:
    print(best)
    sys.exit(0)

sys.exit(1)
