#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Launcher de vLLM (OpenAI-compatible).")
    parser.add_argument("--model", default=os.getenv("LUCY_VLLM_MODEL", "qwen2.5-32b"))
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--max-context", type=int, default=32768)
    parser.add_argument("--quantization", default=os.getenv("LUCY_VLLM_QUANT", "awq"))
    parser.add_argument("--gpu-mem", type=float, default=0.85)
    parser.add_argument("--tensor-parallel", type=int, default=1)
    args = parser.parse_args()

    cmd = [
        sys.executable,
        "-m",
        "vllm.entrypoints.openai.api_server",
        "--model",
        args.model,
        "--host",
        args.host,
        "--port",
        str(args.port),
        "--max-model-len",
        str(args.max_context),
        "--gpu-memory-utilization",
        str(args.gpu_mem),
        "--tensor-parallel-size",
        str(args.tensor_parallel),
    ]
    if args.quantization:
        cmd += ["--quantization", args.quantization]

    print("Ejecutando:", " ".join(cmd))
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
