#!/usr/bin/env python3
"""
Lucy Desktop Agent (versión mínima de manos locales)

- Loop interactivo en consola.
- Ejecuta comandos "de escritorio" con filtros de seguridad.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from typing import List

# Comandos iniciales permitidos (primer token)
SAFE_PREFIXES: List[str] = [
    "xdg-open",
    "gio",
    "firefox",
    "vlc",
    "code",
    "nautilus",
    "thunar",
    "gnome-screenshot",
    "gnome-terminal",
    "google-chrome",
    "chromium",
    "evince",
    "okular",
    "gedit",
    "libreoffice",
]

# Subcadenas peligrosas bloqueadas
BANNED_SUBSTRINGS: List[str] = [
    " rm -rf",
    " rm -r ",
    " rm -f ",
    "mkfs",
    "dd if=",
    "mkpartition",
    "parted ",
    "wipefs",
    "cryptsetup",
    "userdel",
    "groupdel",
    "shutdown",
    "reboot",
    "poweroff",
    ":(){:|:&};:",
    "> /dev/sd",
    ">/dev/sd",
]


def is_safe_command(command: str) -> bool:
    """Heurística de seguridad básica para comandos."""
    normalized = command.strip()
    if not normalized:
        return False

    # Nunca permitimos sudo
    if normalized.startswith("sudo "):
        print("[LucyDesktop] Bloqueado: no se permite 'sudo'.", file=sys.stderr)
        return False

    lower = normalized.lower()
    for bad in BANNED_SUBSTRINGS:
        if bad in lower:
            print(f"[LucyDesktop] Bloqueado por patrón peligroso: {bad!r}", file=sys.stderr)
            return False

    # Primer token debe estar en SAFE_PREFIXES
    try:
        first_token = shlex.split(normalized)[0]
    except ValueError as exc:
        print(f"[LucyDesktop] No pude parsear el comando: {exc}", file=sys.stderr)
        return False

    if first_token not in SAFE_PREFIXES:
        print(
            f"[LucyDesktop] Bloqueado: el comando inicial {first_token!r} "
            "no está en SAFE_PREFIXES.",
            file=sys.stderr,
        )
        return False

    return True


def run_command(command: str) -> int:
    """Ejecuta un comando si pasa los filtros."""
    print(f"[LucyDesktop] Pedido de ejecución: {command!r}")
    if not is_safe_command(command):
        print("[LucyDesktop] Comando rechazado por seguridad.", file=sys.stderr)
        return 1

    try:
        completed = subprocess.run(command, shell=True, check=False)
        return completed.returncode
    except KeyboardInterrupt:
        print("\n[LucyDesktop] Interrumpido por el usuario.", file=sys.stderr)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"[LucyDesktop] Error al ejecutar el comando: {exc}", file=sys.stderr)
        return 1


def interactive_loop() -> int:
    """Loop interactivo simple."""
    print("Lucy Desktop Agent (modo interactivo).")
    print("Escribí un comando de escritorio o 'salir' para terminar.\n")

    while True:
        try:
            line = input("lucy-desktop> ")
        except EOFError:
            print("\n[LucyDesktop] EOF recibido, saliendo.")
            return 0
        except KeyboardInterrupt:
            print("\n[LucyDesktop] Ctrl+C, saliendo.")
            return 130

        line = line.strip()
        if not line:
            continue

        if line.lower() in {"salir", "exit", "quit"}:
            print("[LucyDesktop] Chau 💜")
            return 0

        rc = run_command(line)
        print(f"[LucyDesktop] Código de salida: {rc}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Lucy Desktop Agent – manos locales con filtros de seguridad.",
    )
    parser.add_argument(
        "-c",
        "--command",
        help="Comando único a ejecutar; si se omite, entra en modo interactivo.",
    )
    args = parser.parse_args(argv)

    if args.command:
        return run_command(args.command)

    return interactive_loop()


if __name__ == "__main__":
    raise SystemExit(main())
