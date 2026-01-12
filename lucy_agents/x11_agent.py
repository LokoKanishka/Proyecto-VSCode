#!/usr/bin/env python3
from __future__ import annotations

import os
import socket
import subprocess
import threading
from pathlib import Path
from typing import Optional, Tuple


def _resolve_unix_sock_path() -> Path:
    env = os.environ.get("X11_AGENT_SOCK", "").strip()
    if env:
        sp = Path(env).expanduser()
        sp.parent.mkdir(parents=True, exist_ok=True)
        return sp

    cache_dir = Path.home() / ".cache" / "lucy"
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        return cache_dir / "x11_agent.sock"
    except Exception:
        pass

    repo_root = Path(__file__).resolve().parents[1]
    diag = repo_root / "diagnostics"
    diag.mkdir(parents=True, exist_ok=True)
    return diag / "x11_agent.sock"


def _parse_tcp(s: str) -> Optional[Tuple[str, int]]:
    s = (s or "").strip()
    if not s or ":" not in s:
        return None
    host, port_s = s.rsplit(":", 1)
    host = host.strip() or "127.0.0.1"
    try:
        return (host, int(port_s.strip()))
    except Exception:
        return None


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
        try:
            conn.close()
        except Exception:
            pass


def _serve_unix(path: Path) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    try:
        path.unlink()
    except FileNotFoundError:
        pass

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(path))
    os.chmod(str(path), 0o600)
    srv.listen(50)

    print(f"x11_agent: unix listening on {path}", flush=True)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=_handle, args=(c,), daemon=True).start()


def _serve_tcp(host: str, port: int) -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(50)

    print(f"x11_agent: tcp listening on {host}:{port}", flush=True)
    while True:
        c, _ = srv.accept()
        threading.Thread(target=_handle, args=(c,), daemon=True).start()


def main() -> None:
    tcp = _parse_tcp(os.environ.get("X11_AGENT_TCP", ""))
    unix_path = _resolve_unix_sock_path()

    if tcp:
        threading.Thread(target=_serve_tcp, args=tcp, daemon=True).start()

    _serve_unix(unix_path)


if __name__ == "__main__":
    main()
