#!/usr/bin/env python3
"""
Lucy Desktop Bridge

Puente simple entre los agentes de Lucy (voz, web, etc.)
y el Lucy Desktop Agent (manos locales).

Uso interno en Python:

    from lucy_agents.desktop_bridge import run_desktop_command
    run_desktop_command("code .")

Uso desde consola:

    python -m lucy_agents.desktop_bridge --command "code ."
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from typing import Optional

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DESKTOP_AGENT = PROJECT_ROOT / "scripts" / "lucy_desktop_agent.py"


def run_desktop_command(command: str) -> int:
    """
    Ejecuta un comando a través de Lucy Desktop Agent.

    - No hace filtrado extra de seguridad: eso ya lo hace el propio
      Desktop Agent.
    - Solo se encarga de localizar el launcher y llamarlo.
    """
    print(f"[LucyDesktopBridge] run_desktop_command: {command!r}", flush=True)

    if not command.strip():
        print("[LucyDesktopBridge] Comando vacío, nada que hacer.", flush=True)
        return 0

    if not DESKTOP_AGENT.exists():
        print(
            f"[LucyDesktopBridge] No encontré el Desktop Agent: {DESKTOP_AGENT}",
            flush=True,
        )
        return 1

    try:
        completed = subprocess.run([sys.executable, str(DESKTOP_AGENT), "-c", command])
        return completed.returncode
    except KeyboardInterrupt:
        print("\n[LucyDesktopBridge] Interrumpido por el usuario.", flush=True)
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"[LucyDesktopBridge] Error al ejecutar el comando: {exc}", flush=True)
        return 1


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Puente CLI para Lucy Desktop Agent (run_desktop_command).",
    )
    parser.add_argument(
        "-c",
        "--command",
        required=True,
        help="Comando a ejecutar (por ejemplo: 'code .' o 'xdg-open https://example.com').",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    return run_desktop_command(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
