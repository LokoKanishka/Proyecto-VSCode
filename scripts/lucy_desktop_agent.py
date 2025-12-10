#!/usr/bin/env python3
"""
Lucy Desktop Agent

Puente simple entre Lucy y el sistema operativo.
Ejecuta SOLO comandos permitidos (allowlist) y deja trazas completas
para poder reconstruir qué pasó mirando la consola.
"""

from __future__ import annotations

import shlex
import subprocess
import sys
from typing import List, Tuple, Optional, Sequence, Any


# Binarios permitidos (primer token del comando)
ALLOWED_BINARIES = {
    "xdg-open",
    "code",
    "nautilus",
    "wmctrl",
}


def _log(msg: str) -> None:
    """Log con prefijo estándar."""
    print(f"[LucyDesktop] {msg}", flush=True)


def _parse_command(command_str: str) -> Tuple[bool, List[str]]:
    """
    Parsea y valida el comando.

    Devuelve (allowed, argv_list).
    Si allowed es False, argv_list puede estar vacía.
    """
    command_str = (command_str or "").strip()
    if not command_str:
        _log("Comando vacío recibido.")
        return False, []

    try:
        args = shlex.split(command_str)
    except ValueError as exc:
        _log(f"Error al parsear el comando: {exc}")
        return False, []

    if not args:
        _log("No se encontraron tokens en el comando.")
        return False, []

    binary = args[0]
    if binary not in ALLOWED_BINARIES:
        _log(f"Comando rechazado por allowlist: {args!r}")
        return False, []

    _log(f"Comando aceptado: {args!r}")
    return True, args


def run_once(command_str: str) -> int:
    """Ejecuta un solo comando validado por allowlist."""
    allowed, args = _parse_command(command_str)
    if not allowed:
        return 1

    _log(f"Ejecutando comando: {args!r}")
    try:
        result = subprocess.run(args)
    except Exception as exc:  # noqa: BLE001
        _log(f"Error al ejecutar el comando: {exc}")
        return 1

    _log(f"Exit code: {result.returncode}")
    return result.returncode


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point CLI.

    Uso esperado:
        python3 scripts/lucy_desktop_agent.py -c '<comando>'
    """
    if argv is None:
        argv = sys.argv[1:]

    _log(f"script entry, argv={sys.argv!r}")

    if len(argv) >= 2 and argv[0] == "-c":
        # Todo lo que sigue a -c lo tratamos como un único comando
        command_str = " ".join(argv[1:])
        return run_once(command_str)

    _log("Uso esperado: lucy_desktop_agent.py -c '<comando>'")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
