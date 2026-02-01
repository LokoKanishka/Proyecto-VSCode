#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import time
import shutil
from pathlib import Path

try:
    import psutil  # type: ignore
except Exception:
    psutil = None


def get_cpu_mem():
    if psutil:
        return {
            "cpu_pct": psutil.cpu_percent(interval=None),
            "mem_pct": psutil.virtual_memory().percent,
        }
    return {"cpu_pct": None, "mem_pct": None}


def get_gpu():
    if not shutil.which("nvidia-smi"):
        return {"gpu_mem_pct": None}
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
            text=True,
        )
        used, total = out.strip().split(",")
        used = float(used)
        total = float(total)
        return {"gpu_mem_pct": round(used / total, 3) if total else None}
    except Exception:
        return {"gpu_mem_pct": None}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Profile CPU/mem/GPU into jsonl")
    parser.add_argument("--out", default="logs/session_profile.jsonl")
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--duration", type=float, default=30.0)
    args = parser.parse_args()

    Path(os.path.dirname(args.out) or ".").mkdir(parents=True, exist_ok=True)
    end = time.time() + args.duration
    with open(args.out, "w", encoding="utf-8") as fh:
        while time.time() < end:
            payload = {"ts": time.time(), **get_cpu_mem(), **get_gpu()}
            fh.write(json.dumps(payload) + "\n")
            fh.flush()
            time.sleep(args.interval)
    print(f"Profile saved to {args.out}")
