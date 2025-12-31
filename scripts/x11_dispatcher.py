#!/usr/bin/env python3
# x11_dispatcher.py
#
# Lucy X11 Agent - Dispatcher (A2.1)
# Contrato: LUCY_X11_AGENT_API.md (A1 + A2.2)

import os
import re
import shlex
import signal
import subprocess
import sys
import time
from typing import Callable, List, Optional, Tuple

# =========================
# Debug opcional (archivo)
# =========================
_DEBUG = os.environ.get("LUCY_DISPATCHER_DEBUG") == "1"
_DEBUG_LOG = os.environ.get("LUCY_DISPATCHER_DEBUG_LOG", "/tmp/lucy_dispatcher_debug.log")

def _d(msg: str):
    if not _DEBUG:
        return
    try:
        with open(_DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(msg.rstrip() + "\n")
    except Exception:
        pass



# =========================
# Errores controlados
# =========================

class LucyError(Exception):
    code = "E_EXEC_FAIL"

    def __init__(self, message: str = ""):
        self.message = message
        super().__init__(message)


class InvalidArg(LucyError):
    code = "E_INVALID_ARG"


class NotFound(LucyError):
    code = "E_NOT_FOUND"


class Timeout(LucyError):
    code = "E_TIMEOUT"


# =========================
# Timeout duro (dispatcher)
# =========================

def _timeout_handler(signum, frame):
    raise Timeout()


# =========================
# Handlers (stubs)
# =========================

FAKE_MODE = os.environ.get("LUCY_DISPATCHER_FAKE") == "1"
DEFAULT_CMD_TIMEOUT = float(os.environ.get("LUCY_DISPATCHER_TIMEOUT", "2"))
signal.signal(signal.SIGALRM, _timeout_handler)
signal.alarm(int(max(1, DEFAULT_CMD_TIMEOUT)))  # timeout global por request (segundos)
WMCTRL_BIN = os.environ.get("LUCY_WMCTRL_BIN") or "/usr/bin/wmctrl"
if not os.path.exists(WMCTRL_BIN):
    WMCTRL_BIN = "wmctrl"
XDOTOOL_BIN = os.environ.get("LUCY_XDOTOOL_BIN") or "/usr/bin/xdotool"
if not os.path.exists(XDOTOOL_BIN):
    XDOTOOL_BIN = "xdotool"
_WID_RE = re.compile(r"^0x[0-9a-fA-F]+$")


def _run_cmd(cmd: List[str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=DEFAULT_CMD_TIMEOUT,
            env=os.environ.copy(),
        )
    except subprocess.TimeoutExpired:
        raise Timeout()
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        msg = f"{cmd[0]} exited with {proc.returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        raise LucyError(msg)
    return proc.stdout


def _run_host_cmd(cmd: str) -> str:
    _d(f"_run_host_cmd: cmd_len={len(cmd)}")
    _d(f"_run_host_cmd: cmd={cmd}")
    host_exec = os.path.join(os.path.dirname(__file__), "x11_host_exec.sh")
    if not os.path.exists(host_exec):
        raise LucyError("x11_host_exec.sh missing")
    env = os.environ.copy()
    env.setdefault("X11_FILE_CALL_TIMEOUT", str(max(1, int(DEFAULT_CMD_TIMEOUT))))
    try:
        proc = subprocess.run(
            [host_exec, cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=DEFAULT_CMD_TIMEOUT,
            env=env,
        )
    except subprocess.TimeoutExpired:
        raise Timeout()
    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        msg = f"host_exec exited with {proc.returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        raise LucyError(msg)
    if proc.stdout is None:
        detail = (proc.stderr or "").strip()
        msg = "host_exec returned None stdout"
        if detail:
            msg = f"{msg}: {detail}"
        raise LucyError(msg)
    return proc.stdout


def _parse_wmctrl_output(out: str) -> List[str]:
    lines: List[str] = []
    for line in out.splitlines():
        line = line.rstrip()
        if not line:
            continue
        parts = line.split(None, 4)
        if len(parts) < 4:
            continue
        wid, desktop, cls = parts[0], parts[1], parts[2]
        title = parts[4] if len(parts) > 4 else ""
        lines.append(f"{wid}\t{desktop}\t{cls}\t{title}")
    return lines


def do_list_windows() -> List[str]:
    if FAKE_MODE:
        return [
            "0x03a00004\t0\tcode.Code\tProyecto-VSCode - Visual Studio Code",
            "0x01e0001c\t0\tgoogle-chrome.Google-chrome\tChatGPT",
        ]
    out = _run_cmd([WMCTRL_BIN, "-lx"])
    return _parse_wmctrl_output(out)


def _host_list_windows() -> List[str]:
    # Host list via file-IPC. Nunca debe devolver None.
    out = _run_host_cmd(f"{WMCTRL_BIN} -lx")
    if out is None:
        raise LucyError("host_list_windows: empty stdout (None)")
    return _parse_wmctrl_output(out)


def _default_screenshot_path() -> str:
    base_dir = os.environ.get("LUCY_SCREENSHOT_DIR", "/tmp")
    ts = int(time.time() * 1000)
    pid = os.getpid()
    return os.path.join(base_dir, f"lucy_screenshot_{pid}_{ts}.png")


def _build_screenshot_cmd(target: str, out_path: str) -> str:
    target_q = shlex.quote(target)
    out_q = shlex.quote(out_path)
    lines = [
        "set -euo pipefail",
        f"TARGET={target_q}",
        f"OUT={out_q}",
        'mkdir -p "$(dirname "$OUT")"',
        "if command -v import >/dev/null 2>&1; then",
        '  if [ "$TARGET" = "root" ]; then',
        '    import -window root "$OUT"',
        "  else",
        '    import -window "$TARGET" "$OUT"',
        "  fi",
        "elif command -v maim >/dev/null 2>&1; then",
        '  if [ "$TARGET" = "root" ]; then',
        '    maim "$OUT"',
        "  else",
        '    if wid_dec=$(printf "%d" "$TARGET" 2>/dev/null); then',
        '      maim -i "$wid_dec" "$OUT"',
        "    else",
        '      maim -i "$TARGET" "$OUT"',
        "    fi",
        "  fi",
        "elif command -v xwd >/dev/null 2>&1; then",
        '  if command -v convert >/dev/null 2>&1; then',
        '    if [ "$TARGET" = "root" ]; then',
        '      xwd -root -silent | convert xwd:- "$OUT"',
        "    else",
        '      xwd -id "$TARGET" -silent | convert xwd:- "$OUT"',
        "    fi",
        "  elif command -v magick >/dev/null 2>&1; then",
        '    if [ "$TARGET" = "root" ]; then',
        '      xwd -root -silent | magick xwd:- "$OUT"',
        "    else",
        '      xwd -id "$TARGET" -silent | magick xwd:- "$OUT"',
        "    fi",
        "  else",
        '    echo "missing convert/magick" >&2',
        "    exit 127",
        "  fi",
        "else",
        '  echo "no screenshot tool available" >&2',
        "  exit 127",
        "fi",
    ]
    return "\n".join(lines)


def _read_png_size(path: str) -> Optional[Tuple[int, int]]:
    try:
        with open(path, "rb") as f:
            header = f.read(24)
        if len(header) < 24:
            return None
        if header[:8] != b"\x89PNG\r\n\x1a\n":
            return None
        if header[12:16] != b"IHDR":
            return None
        width = int.from_bytes(header[16:20], "big")
        height = int.from_bytes(header[20:24], "big")
        if width <= 0 or height <= 0:
            return None
        return width, height
    except Exception:
        return None


def do_find_window(pattern: str) -> List[str]:
    if not pattern:
        raise InvalidArg("empty pattern")
    pat = pattern.lower()
    for line in do_list_windows():
        parts = line.split("\t", 3)
        if len(parts) != 4:
            continue
        wid, _desktop, klass, title = parts
        if pat in (klass or "").lower() or pat in (title or "").lower():
            return [f"{wid}\t{klass}\t{title}"]
    raise NotFound()


def do_focus_window(wid: str) -> None:
    if not _WID_RE.match(wid or ""):
        raise InvalidArg("invalid wid")
    if FAKE_MODE:
        return None
    exists = False
    for line in do_list_windows():
        parts = line.split("\t", 1)
        if parts and parts[0] == wid:
            exists = True
            break
    if not exists:
        raise NotFound()
    _run_cmd([WMCTRL_BIN, "-ia", wid])
    return None


def do_send_keys(wid: str, keys: str) -> None:
    if not _WID_RE.match(wid or ""):
        raise InvalidArg("invalid wid")
    if not keys:
        raise InvalidArg("missing keys")
    if FAKE_MODE:
        return None
    exists = False
    for line in do_list_windows():
        parts = line.split("\t", 1)
        if parts and parts[0] == wid:
            exists = True
            break
    if not exists:
        raise NotFound()
    _run_cmd([WMCTRL_BIN, "-i", "-R", wid])
    _run_cmd([XDOTOOL_BIN, "windowactivate", "--sync", wid, "key", keys])
    return None


def do_type_text(wid: str, text: str) -> None:
    if not _WID_RE.match(wid or ""):
        raise InvalidArg("invalid wid")
    if not text:
        raise InvalidArg("missing text")
    if FAKE_MODE:
        return None
    exists = False
    for line in do_list_windows():
        parts = line.split("\t", 1)
        if parts and parts[0] == wid:
            exists = True
            break
    if not exists:
        raise NotFound()
    _run_cmd([WMCTRL_BIN, "-i", "-R", wid])
    _run_cmd(
        [XDOTOOL_BIN, "windowactivate", "--sync", wid, "type", "--delay", "0", "--", text]
    )
    return None


def do_screenshot(target: str) -> List[str]:
    _d(f"do_screenshot: enter target={target}")
    if not target:
        raise InvalidArg("invalid target")
    if target != "root" and not _WID_RE.match(target):
        raise InvalidArg("invalid target")

    if target != "root":
        windows = do_list_windows() if FAKE_MODE else _host_list_windows()
        exists = False
        for line in windows:
            parts = line.split("\t", 1)
            if parts and parts[0] == target:
                exists = True
                break
        if not exists:
            raise NotFound()

    if FAKE_MODE:
        return ["PATH /tmp/lucy_test.png WIDTH 100 HEIGHT 100"]
    out_path = _default_screenshot_path()
    _d(f"do_screenshot: out_path={out_path}")
    # Backend estable en este entorno: ImageMagick 'import' (xwd|convert falla con BadColor).
    # Ejecutamos directo via host_exec para evitar scripts multilínea y reducir puntos de fallo.
    _run_host_cmd(f"import -window {target} {out_path}")
    if not os.path.exists(out_path):
        raise LucyError("screenshot missing")

    size = _read_png_size(out_path)
    if size:
        width, height = size
        return [f"PATH {out_path} WIDTH {width} HEIGHT {height}"]
    return [f"PATH {out_path}"]


# =========================
# Tabla de dispatch
# =========================

DISPATCH_TABLE: dict[str, Callable[..., object]] = {
    "list_windows": do_list_windows,
    "find_window": do_find_window,
    "focus_window": do_focus_window,
    "send_keys": do_send_keys,
    "type_text": do_type_text,
    "screenshot": do_screenshot,
}


# =========================
# Parsing
# =========================

def parse_request(line: str) -> Tuple[Optional[str], str]:
    line = line.strip()
    if not line:
        return None, ""

    if " " in line:
        action, rest = line.split(" ", 1)
        argstr = rest.strip()
    else:
        action = line
        argstr = ""

    return action, argstr


# =========================
# Dispatcher principal
# =========================

def main():
    try:
        if len(sys.argv) > 1:
            action = sys.argv[1].strip()
            argstr = " ".join(sys.argv[2:]).strip()
        else:
            raw = sys.stdin.readline()
            if not raw:
                return
            action, argstr = parse_request(raw)
            if action is None:
                return
        if not action:
            return

        if action not in DISPATCH_TABLE:
            raise InvalidArg(f"unknown action: {action}")

        handler = DISPATCH_TABLE[action]
        arg_tokens = argstr.split() if argstr else []

        # Validacion de aridad antes de ejecutar
        if action == "list_windows":
            if arg_tokens:
                raise InvalidArg("too many arguments")
            result = handler()

        elif action == "find_window":
            if not arg_tokens:
                raise InvalidArg("missing pattern")
            if len(arg_tokens) > 1:
                raise InvalidArg("too many arguments")
            result = handler(arg_tokens[0])

        elif action == "focus_window":
            if not arg_tokens:
                raise InvalidArg("missing wid")
            if len(arg_tokens) > 1:
                raise InvalidArg("too many arguments")
            result = handler(arg_tokens[0])

        elif action == "send_keys":
            if not arg_tokens:
                raise InvalidArg("missing wid")
            if len(arg_tokens) < 2:
                raise InvalidArg("missing keys")
            if len(arg_tokens) > 2:
                raise InvalidArg("too many arguments")
            wid, keys = arg_tokens[0], arg_tokens[1]
            result = handler(wid, keys)

        elif action == "type_text":
            if not arg_tokens:
                raise InvalidArg("missing wid")
            if len(arg_tokens) < 2:
                raise InvalidArg("missing text")
            if len(arg_tokens) > 2:
                raise InvalidArg("too many arguments")
            wid, text = argstr.split(" ", 1)
            result = handler(wid, text)

        elif action == "screenshot":
            if not arg_tokens:
                raise InvalidArg("missing target")
            if len(arg_tokens) > 1:
                raise InvalidArg("too many arguments")
            result = handler(arg_tokens[0])

        # Normalizar salida
        if result is None:
            print("OK")
        elif isinstance(result, list):
            for line in result:
                print(line)
        else:
            print(result)

    except LucyError as e:
        print(f"ERR {e.code} {e.message}".rstrip())
    except Exception:
        print("ERR E_EXEC_FAIL")
    finally:
        signal.alarm(0)


if __name__ == "__main__":
    main()
