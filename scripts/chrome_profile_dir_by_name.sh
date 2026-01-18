#!/usr/bin/env bash
set -euo pipefail

NAME="${1:-}"
if [ -z "${NAME:-}" ]; then
  echo "USAGE: chrome_profile_dir_by_name.sh <profile_name>" >&2
  exit 2
fi

python3 - "$NAME" <<'PY'
import json
import os
import sys
from pathlib import Path

want = sys.argv[1].strip().lower()
paths = []

override = os.environ.get("CHROME_LOCAL_STATE")
if override:
    p = Path(override)
    if p.is_dir():
        p = p / "Local State"
    paths.append(p)
else:
    for base in ("google-chrome", "chromium", "google-chrome-beta", "google-chrome-unstable"):
        paths.append(Path.home() / ".config" / base / "Local State")

available = []
for p in paths:
    if not p.exists():
        continue
    try:
        data = json.loads(p.read_text(encoding="utf-8", errors="ignore"))
    except Exception:
        continue
    info = ((data.get("profile") or {}).get("info_cache")) or {}
    for prof_dir, meta in info.items():
        meta = meta or {}
        name = (meta.get("name") or "").strip()
        base = str(p.parent)
        if name:
            available.append((name, prof_dir, base))
        if name.lower() == want:
            print(f"PROFILE_DIR={prof_dir}")
            print(f"BASE={base}")
            raise SystemExit(0)

if available:
    for name, prof_dir, base in available:
        print(f"AVAILABLE name={name} dir={prof_dir} base={base}", file=sys.stderr)
raise SystemExit(3)
PY
