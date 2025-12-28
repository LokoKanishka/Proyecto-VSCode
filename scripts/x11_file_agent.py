#!/usr/bin/env python3
from __future__ import annotations

import os
import time
import subprocess
from pathlib import Path

POLL_SECS = float(os.environ.get("X11_FILE_AGENT_POLL", "0.15"))

def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]

def ipc_dir() -> Path:
    env = os.environ.get("X11_FILE_IPC_DIR", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    return (repo_root() / "diagnostics" / "x11_file_ipc").resolve()

def ensure_dirs(base: Path) -> tuple[Path, Path]:
    inbox = base / "inbox"
    outbox = base / "outbox"
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    return inbox, outbox

def x11_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("DISPLAY", ":0")
    if "XAUTHORITY" not in env:
        uid = os.getuid()
        cand = f"/run/user/{uid}/gdm/Xauthority"
        env["XAUTHORITY"] = cand if os.path.exists(cand) else str(Path.home() / ".Xauthority")
    return env

def handle_req(req_path: Path, outbox: Path) -> None:
    token = req_path.stem.replace("req_", "", 1)
    out_path = outbox / f"res_{token}.txt"
    cmd = req_path.read_text(encoding="utf-8", errors="replace").strip()

    if not cmd:
        out_path.write_text("RC=2\nERROR: comando vacío\n", encoding="utf-8")
        try: req_path.unlink()
        except Exception: pass
        return

    p = subprocess.run(
        ["/bin/bash", "-lc", cmd],
        env=x11_env(),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    out_path.write_text(f"RC={p.returncode}\n{p.stdout}", encoding="utf-8", errors="replace")

    try:
        req_path.unlink()
    except Exception:
        pass

def main() -> int:
    base = ipc_dir()
    inbox, outbox = ensure_dirs(base)
    print(f"x11_file_agent: IPC={base}", flush=True)
    print(f"x11_file_agent: inbox={inbox}", flush=True)
    print(f"x11_file_agent: outbox={outbox}", flush=True)

    while True:
        reqs = sorted(inbox.glob("req_*.txt"), key=lambda p: p.stat().st_mtime)
        if not reqs:
            time.sleep(POLL_SECS)
            continue
        for req in reqs:
            try:
                handle_req(req, outbox)
            except Exception as e:
                # si algo explotó, intentamos dejar rastro
                try:
                    token = req.stem.replace("req_", "", 1)
                    (outbox / f"res_{token}.txt").write_text(f"RC=1\nERROR: {e}\n", encoding="utf-8")
                except Exception:
                    pass
        time.sleep(0.01)

if __name__ == "__main__":
    raise SystemExit(main())
