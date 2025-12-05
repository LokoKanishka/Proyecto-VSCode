#!/usr/bin/env python3
"""
Lucy Desktop Agent (manos locales mínimas + lectura de archivos)

Modos de uso:
- Interactivo:
    ./scripts/lucy_desktop_agent.sh

    Comandos internos (no van al shell):
        ls [RUTA]
        read RUTA

    Comandos de escritorio (van al shell con filtros):
        xdg-open URL
        code .
        nautilus .
        etc. (ver SAFE_PREFIXES)

- Comando único:
    ./scripts/lucy_desktop_agent.sh -c "xdg-open https://www.google.com"
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Comandos iniciales permitidos (primer token, para shell)
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

# Raíces "amigables" para mensajes en ls/read
PROJECT_ROOT = Path(__file__).resolve().parents[1]
HOME_DIR = Path.home()


# ===============================
# 1. Comandos internos: ls, read
# ===============================

def handle_internal(command: str) -> Tuple[bool, int]:
    """
    Maneja comandos internos:
      - ls [RUTA]
      - read RUTA

    Devuelve (handled, return_code).
    handled = True si el comando era interno (aunque falle).
    """
    stripped = command.strip()
    if not stripped:
        return False, 0

    parts = stripped.split(maxsplit=1)
    cmd = parts[0]
    arg = parts[1] if len(parts) > 1 else ""

    if cmd == "ls":
        return True, internal_ls(arg)

    if cmd == "read":
        return True, internal_read(arg)

    return False, 0


def _pretty_path(p: Path) -> str:
    try:
        p = p.resolve()
    except Exception:  # noqa: BLE001
        return str(p)
    try:
        return str(p).replace(str(PROJECT_ROOT), "<PROYECTO>").replace(str(HOME_DIR), "<HOME>")
    except Exception:  # noqa: BLE001
        return str(p)


def internal_ls(path_arg: str) -> int:
    """Implementación simple de 'ls [ruta]'."""
    target = Path(path_arg) if path_arg else Path.cwd()
    try:
        target = target.expanduser().resolve()
    except Exception as exc:  # noqa: BLE001
        print(f"[LucyDesktop][ls] No pude resolver la ruta: {exc}", file=sys.stderr)
        return 1

    if not target.exists():
        print(f"[LucyDesktop][ls] La ruta no existe: {target}", file=sys.stderr)
        return 1
    if not target.is_dir():
        print(f"[LucyDesktop][ls] No es un directorio: {target}", file=sys.stderr)
        return 1

    print(f"[LucyDesktop][ls] Contenido de {_pretty_path(target)}:")
    try:
        entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
    except PermissionError:
        print("[LucyDesktop][ls] Permiso denegado para listar este directorio.", file=sys.stderr)
        return 1

    if not entries:
        print("  (vacío)")
        return 0

    for entry in entries:
        mark = "/" if entry.is_dir() else ""
        print(f"  {entry.name}{mark}")
    return 0


def internal_read(path_arg: str) -> int:
    """Implementación de 'read RUTA': muestra contenido de un archivo de texto."""
    if not path_arg:
        print("[LucyDesktop][read] Uso: read RUTA/AL/ARCHIVO", file=sys.stderr)
        return 1

    target = Path(path_arg).expanduser()
    try:
        target = target.resolve()
    except Exception as exc:  # noqa: BLE001
        print(f"[LucyDesktop][read] No pude resolver la ruta: {exc}", file=sys.stderr)
        return 1

    if not target.exists():
        print(f"[LucyDesktop][read] El archivo no existe: {target}", file=sys.stderr)
        return 1
    if not target.is_file():
        print(f"[LucyDesktop][read] No es un archivo: {target}", file=sys.stderr)
        return 1

    print(f"[LucyDesktop][read] Leyendo {_pretty_path(target)}:\n")
    try:
        # Leemos en modo texto con fallback a UTF-8
        with target.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                # Evitar prints hiperlargos en archivos gigantes: cortamos después de cierto límite
                # pero por ahora lo dejamos sin límite y más adelante se puede ajustar.
                print(line.rstrip("\n"))
    except PermissionError:
        print("[LucyDesktop][read] Permiso denegado para leer el archivo.", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(f"[LucyDesktop][read] Error al leer el archivo: {exc}", file=sys.stderr)
        return 1

    return 0


# ==========================
# 2. Comandos de escritorio
# ==========================

def is_safe_command(command: str) -> bool:
    """Heurística de seguridad básica para comandos de shell."""
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


def run_shell_command(command: str) -> int:
    """Ejecuta un comando de shell si pasa los filtros."""
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


# ====================
# 3. Loop interactivo
# ====================

def interactive_loop() -> int:
    """Loop interactivo simple."""
    print("Lucy Desktop Agent (modo interactivo).")
    print("Comandos internos:")
    print("  ls [RUTA]   → listar contenido de carpeta")
    print("  read RUTA   → leer archivo de texto")
    print("Comandos de escritorio (van al sistema si son seguros):")
    print("  xdg-open URL, code ., nautilus ., etc.")
    print("Escribí 'salir' para terminar.\n")

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

        # 1) Intentar comandos internos (ls, read)
        handled, rc = handle_internal(line)
        if handled:
            print(f"[LucyDesktop] Código de salida (interno): {rc}\n")
            continue

        # 2) Si no es interno, mandarlo al shell con filtros
        rc = run_shell_command(line)
        print(f"[LucyDesktop] Código de salida: {rc}\n")


# ===========
# 4. main()
# ===========

def main(argv: List[str] | None = None) -> int:
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
        # Primero intentamos tratarlo como comando interno
        handled, rc = handle_internal(args.command)
        if handled:
            return rc
        return run_shell_command(args.command)

    return interactive_loop()


if __name__ == "__main__":
    raise SystemExit(main())
