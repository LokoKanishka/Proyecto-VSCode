#!/usr/bin/env python3
import argparse
import os
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Stub de preparación RICO -> YOLO.")
    parser.add_argument("--rico-root", required=True, help="Root del dataset RICO")
    parser.add_argument("--out-dir", default="data/rico_yolo")
    args = parser.parse_args()

    rico_root = Path(args.rico_root)
    out_dir = Path(args.out_dir)
    if not rico_root.exists():
        print(f"No existe RICO: {rico_root}")
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "images").mkdir(exist_ok=True)
    (out_dir / "labels").mkdir(exist_ok=True)

    print("Stub listo. Aquí deberías convertir JSON -> labels YOLO.")
    print(f"Salida preparada en: {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
