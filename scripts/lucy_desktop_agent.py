#!/usr/bin/env python3
"""
Lucy Desktop Agent

Puente simple y bien logueado entre Lucy y el sistema operativo.
Ejecuta SOLO comandos permitidos (allowlist) y deja trazas completas
para que se pueda reconstruir qué pasó mirando la consola.
"""

import sys
import shlex
import subprocess
from typing import List, Tuple


def _log(msg: str) -> None:
    """Log con prefijo estándar."""
    print(f"[LucyDesktop] {msg}", flush=True)


# Log de entrada SIEMPRE que se cargue el script como programa
_log(f"script entry, argv={sys.argv!r}")


# Binaries permitidos (primer token del comando)
ALLOWED_BINARIES = {
    "xdg-open",
    "code",
    "nautilus",
    "wmctrl",
}


def _parse_command(command_str: str) -> Tuple[bool, List[str]]:
    """
    Parsea y valida el comando.
    Devuelve (allowed, argv_list).
    Si allowed es False, argv_list puede estar vacío.
    """
    command_str = (command_str or "").strip()
    if not command_str:
        _log("Comando vacío recibido.")
        return False, []

    try:
        args = shlex.split(command_str)
    except ValueError as exc:
        _log(f"Error al parsear el comando: {exc!r}")
        return False, []

    if not args:
        _log("Sin tokens luego de parsear el comando.")
        return False, []

    prog = args[0]
    if prog not in ALLOWED_BINARIES:
        _log(f"Programa no permitido: {prog!r}")
        return False, []

    # Caso especial: wmctrl -c "<title>"
    if prog == "wmctrl":
        if len(args) >= 3 and args[1] == "-c":
            title = args[2]
            safe_title = title.replace('"', "").strip()
            if not safe_title:
                _log("Título de ventana vacío/invalid para wmctrl -c.")
                return False, []
            if len(safe_title) > 100:
                _log("Título de ventana demasiado largo para wmctrl -c.")
                return False, []
            # Reescribimos argumentos con el título saneado
            args = ["wmctrl", "-c", safe_title]
            _log(f"wmctrl -c permitido para ventana: {safe_title!r}")
            return True, args
        else:
            _log("wmctrl sólo se permite como 'wmctrl -c <window_title>'.")
            return False, []

    # Otros comandos permitidos tal cual (xdg-open, code, nautilus)
    return True, args


def _run_allowed_command(args: List[str]) -> int:
    """Ejecuta el comando ya validado y loguea resultado."""
    if not args:
        _log("No hay argumentos para ejecutar.")
        return 1

    command_str = " ".join(shlex.quote(a) for a in args)
    _log(f"Running allowed command: {command_str!r}")

    try:
        proc = subprocess.run(
            args,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # noqa: BLE001
        _log(f"Error ejecutando comando: {exc!r}")
        return 1

    _log(f"Command exit code: {proc.returncode}")
    if proc.stdout:
        _log(f"stdout: {proc.stdout!r}")
    if proc.stderr:
        _log(f"stderr: {proc.stderr!r}")

    return proc.returncode


def main() -> int:
    """Punto de entrada principal del Desktop Agent."""
    _log(f"main() argv={sys.argv!r}")

    if len(sys.argv) < 3 or sys.argv[1] != "-c":
        _log("Uso: lucy_desktop_agent.py -c '<comando>'")
        return 1

    command_str = sys.argv[2]
    _log(f"Pedido de ejecución: {command_str!r}")

    allowed, args = _parse_command(command_str)
    if not allowed:
        _log(f"Command rejected (not in allowlist): {command_str!r}")
        return 1

    return _run_allowed_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
