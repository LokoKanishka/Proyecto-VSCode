#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys
from pathlib import Path


def _run(path: str, extra: list[str]) -> int:
    return subprocess.call([sys.executable, path, *extra])


def main() -> int:
    parser = argparse.ArgumentParser(description="Lucy unified entrypoint")
    parser.add_argument(
        "--mode",
        choices=("swarm", "gui", "web", "legacy_ollama"),
        default=os.getenv("LUCY_MODE", "swarm"),
        help="Modo de arranque: swarm | gui | web | legacy_ollama",
    )
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Habilita audio en el swarm (Ear/Mouth workers).",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        help="Habilita consola interactiva para publicar input al swarm.",
    )
    parser.add_argument(
        "--ws-gateway",
        action="store_true",
        help="Habilita WebSocket gateway para el bus del swarm.",
    )
    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Argumentos extra para el script objetivo",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("PYTHONPATH", str(root))

    if args.mode == "swarm":
        if args.voice:
            os.environ["LUCY_SWARM_ENABLE_AUDIO"] = "1"
        if args.console:
            os.environ["LUCY_SWARM_CONSOLE"] = "1"
        if args.ws_gateway:
            os.environ["LUCY_WS_GATEWAY"] = "1"
        target = root / "src" / "engine" / "swarm_runner.py"
    elif args.mode == "gui":
        print("⚠️  Modo gui es legacy (stack OllamaEngine).")
        target = root / "src" / "gui" / "main.py"
    elif args.mode == "web":
        print("⚠️  Modo web es legacy (stack lucy_web).")
        target = root / "lucy_web" / "app.py"
    else:
        print("⚠️  Modo legacy_ollama usa src/main.py (stack antiguo).")
        target = root / "src" / "main.py"

    return _run(str(target), args.extra)


if __name__ == "__main__":
    raise SystemExit(main())
