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
        choices=("gui", "swarm", "web"),
        default=os.getenv("LUCY_MODE", "gui"),
        help="Modo de arranque: gui | swarm | web",
    )
    parser.add_argument(
        "extra",
        nargs=argparse.REMAINDER,
        help="Argumentos extra para el script objetivo",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault("PYTHONPATH", str(root))

    if args.mode == "gui":
        target = root / "src" / "gui" / "main.py"
    elif args.mode == "swarm":
        target = root / "src" / "engine" / "swarm_runner.py"
    else:
        target = root / "lucy_web" / "app.py"

    return _run(str(target), args.extra)


if __name__ == "__main__":
    raise SystemExit(main())
