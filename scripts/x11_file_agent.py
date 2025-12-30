#!/usr/bin/env python3
import os, sys, time, glob, subprocess, pathlib, re

IPC_DIR = os.environ.get("X11_FILE_IPC_DIR")
if not IPC_DIR:
    print("x11_file_agent: ERROR: X11_FILE_IPC_DIR no seteado", file=sys.stderr)
    sys.exit(2)

IPC = pathlib.Path(IPC_DIR)
INBOX  = IPC / "inbox"
OUTBOX = IPC / "outbox"
PAYLOADS = IPC / "payloads"
for d in (INBOX, OUTBOX, PAYLOADS):
    d.mkdir(parents=True, exist_ok=True)

LOG = IPC / "agent.log"

def log(msg: str):
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass

# Timeout por request (segundos)
DEFAULT_TIMEOUT = float(os.environ.get("X11_FILE_AGENT_TIMEOUT", "6"))

# IMPORTANTÍSIMO: evitar recursión.
# Si el agent hereda X11_FILE_IPC_DIR, cualquier x11_run.sh vuelve a llamar x11_file_call.sh.
# Entonces: al ejecutar comandos, removemos X11_FILE_IPC_DIR del entorno.
def run_cmd(cmd: str, timeout_s: float):
    # Preservamos el entorno completo (DISPLAY/XAUTHORITY/etc.) y solo limpiamos wrappers.
    env = os.environ.copy()
    env.pop("X11_FILE_IPC_DIR", None)
    env["X11_FORCE_LOCAL"] = "1"  # bandera por si la usamos luego en x11_run.sh
    wrap_dir = (pathlib.Path(__file__).resolve().parent / "x11_wrap").resolve()
    path_val = env.get("PATH", "")
    if path_val:
        parts = [p for p in path_val.split(":") if p]
        parts = [p for p in parts if os.path.realpath(p) != str(wrap_dir)]
        new_path = ":".join(parts)
        if new_path != path_val:
            env["PATH"] = new_path
    # Ejecutamos con bash -lc para compatibilidad con el resto de tus scripts
    p = subprocess.Popen(
        ["bash", "-lc", cmd],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
        preexec_fn=os.setsid,
    )
    try:
        out, _ = p.communicate(timeout=timeout_s)
        rc = p.returncode if p.returncode is not None else 0
        return rc, out or ""
    except subprocess.TimeoutExpired:
        try:
            os.killpg(p.pid, 15)
        except Exception:
            pass
        time.sleep(0.15)
        try:
            os.killpg(p.pid, 9)
        except Exception:
            pass
        return 124, ""

def parse_req(path: pathlib.Path):
    # req_<ts>_<rand>.txt  → res_<ts>_<rand>.txt
    m = re.match(r"req_(\d+)_([0-9]+)\.txt$", path.name)
    if not m:
        return None
    ts, rid = m.group(1), m.group(2)
    res = OUTBOX / f"res_{ts}_{rid}.txt"
    return ts, rid, res

log(f"x11_file_agent: IPC={IPC}")
log(f"x11_file_agent: inbox={INBOX}")
log(f"x11_file_agent: outbox={OUTBOX}")

# Loop simple: polling corto (sin depender de stdin)
while True:
    try:
        reqs = sorted(INBOX.glob("req_*.txt"), key=lambda p: p.stat().st_mtime)
    except Exception:
        reqs = []

    if not reqs:
        time.sleep(0.05)
        continue

    for req in reqs:
        parsed = parse_req(req)
        if not parsed:
            continue
        ts, rid, res = parsed

        try:
            cmd = req.read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            cmd = ""

        # Si está vacío, respondemos igual para no bloquear al caller
        timeout_s = DEFAULT_TIMEOUT

        rc, out = run_cmd(cmd, timeout_s)

        # Escribimos respuesta (incluye rc, por si el caller quiere debug)
        payload = f"RC={rc}\n"
        if out:
            payload += out
            if not payload.endswith("\n"):
                payload += "\n"

        tmp = res.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8", errors="replace")
        tmp.replace(res)

        # Archivamos el req para no re-procesarlo (y para post-mortem)
        try:
            req.rename(PAYLOADS / req.name)
        except Exception:
            try:
                req.unlink()
            except Exception:
                pass
