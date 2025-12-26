#!/usr/bin/env python3
from __future__ import annotations

import os
import socket
import subprocess
import threading
from pathlib import Path


def _resolve_sock_path() -> Path:
    # 1) override explícito
    env = os.environ.get("X11_AGENT_SOCK", "").strip()
    if env:
        sp = Path(env).expanduser()
        sp.parent.mkdir(parents=True, exist_ok=True)
        return sp

    # 2) default clásico (~/.cache/lucy) si se puede escribir
    cache_dir = Path.home() / ".cache" / "lucy"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "x11_agent.sock"
    except Exception:
        pass

    # 3) fallback: workspace (diagnostics)
    repo_root = Path(__file__).resolve().parents[1]
    diag = repo_root / "diagnostics"
    diag.mkdir(parents=True, exist_ok=True)
    return diag / "x11_agent.sock"


SOCK = _resolve_sock_path()

# limpiar socket viejo si existe
try:
    if SOCK.exists():
        SOCK.unlink()
except FileNotFoundError:
    pass

srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
srv.bind(str(SOCK))
os.chmod(str(SOCK), 0o600)
srv.listen(20)


def _handle(conn: socket.socket) -> None:
    try:
        data = b""
        while not data.endswith(b"\n"):
            chunk = conn.recv(4096)
            if not chunk:
                return
            data += chunk

        cmd = data.decode("utf-8", "replace").rstrip("\n")

        env = os.environ.copy()
        env.setdefault("DISPLAY", ":0")
        if "XAUTHORITY" not in env:
            uid = os.getuid()
            cand = f"/run/user/{uid}/gdm/Xauthority"
            env["XAUTHORITY"] = cand if os.path.exists(cand) else os.path.expanduser("~/.Xauthority")

        p = subprocess.run(
            ["/bin/bash", "-lc", cmd],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        conn.sendall(f"RC={p.returncode}\n".encode("utf-8"))
        conn.sendall(p.stdout.encode("utf-8", "replace"))
    finally:
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()


print(f"x11_agent: listening on {SOCK}", flush=True)
while True:
    c, _ = srv.accept()
    threading.Thread(target=_handle, args=(c,), daemon=True).start()
