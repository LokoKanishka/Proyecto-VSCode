#!/usr/bin/env bash
set -euo pipefail

PROFILE_NAME="${1:-diego}"
EXPECTED_EMAIL="${2:-}"
CONFIG_DIR="${CHROME_CONFIG_DIR:-$HOME/.config/google-chrome}"
LS="$CONFIG_DIR/Local State"

if [ ! -r "$LS" ]; then
  echo "ERROR_NO_LOCAL_STATE: $LS" >&2
  exit 3
fi

python3 - "$PROFILE_NAME" "$EXPECTED_EMAIL" "$LS" <<'PY'
import json, sys
from pathlib import Path

profile_name = sys.argv[1].strip().lower()
expected_email = sys.argv[2].strip().lower()
ls_path = Path(sys.argv[3])

data = json.loads(ls_path.read_text(encoding="utf-8", errors="ignore"))
info = ((data.get("profile") or {}).get("info_cache")) or {}
if not info:
    print("ERROR_NO_INFO_CACHE", file=sys.stderr)
    raise SystemExit(3)

best = None
for prof_dir, v in info.items():
    name = (v.get("name") or "").strip()
    user = (v.get("user_name") or "").strip()
    if name.lower() == profile_name:
        best = (prof_dir, name, user, (v.get("gaia_name") or "").strip())
        break

if not best:
    print(f"ERROR_NO_PROFILE_NAME: {profile_name}", file=sys.stderr)
    raise SystemExit(3)

prof_dir, name, user, gaia = best
if expected_email and user.strip().lower() != expected_email:
    print(f"ERROR_EMAIL_MISMATCH: want={expected_email} got={user}", file=sys.stderr)
    print(f"PROFILE_DIR={prof_dir}")
    print(f"NAME={name}")
    print(f"USER_NAME={user}")
    print(f"GAIA_NAME={gaia}")
    raise SystemExit(3)

print(f"PROFILE_DIR={prof_dir}")
print(f"NAME={name}")
print(f"USER_NAME={user}")
print(f"GAIA_NAME={gaia}")
PY
