#!/usr/bin/env python3
import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Entrenamiento YOLOv8 para UI (stub).")
    parser.add_argument("--data", required=True, help="Path a data.yaml con labels")
    parser.add_argument("--model", default="yolov8n.pt")
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--imgsz", type=int, default=960)
    args = parser.parse_args()

    try:
        from ultralytics import YOLO
    except Exception as exc:
        print(f"ultralytics no disponible: {exc}")
        return 1

    if not os.path.exists(args.data):
        print(f"No existe data file: {args.data}")
        return 1

    model = YOLO(args.model)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
