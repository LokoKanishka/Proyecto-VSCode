#!/usr/bin/env python3
"""
Fusiona un LoRA de GPT-OSS 20B en el modelo base y guarda un checkpoint merged.

Advertencias:
- Consume mucha RAM/VRAM y tiempo; correr en la máquina de Lucy (7950X + 5090).
- Usar un entorno con torch + CUDA; preferir bfloat16/float16 con device_map auto.

Ejemplo:
python tools/merge_gpt_oss_lora.py \
  --base openai/gpt-oss-20b \
  --lora YiwenX/gpt-oss-20b-multilingual-reasoner \
  --out ./models/gpt-oss-20b-multireasoner-merged \
  --dtype bfloat16 \
  --device-map auto
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import Optional

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer


def parse_dtype(value: str) -> torch.dtype:
    """Mapea string → torch.dtype."""
    normalized = value.lower()
    if normalized == "bfloat16":
        return torch.bfloat16
    if normalized in ("float16", "fp16"):
        return torch.float16
    if normalized in ("float32", "fp32"):
        return torch.float32
    raise ValueError(f"Tipo de dato no soportado: {value}")


def merge_lora(
    base_model: str,
    lora_path: str,
    output_dir: Path,
    dtype: torch.dtype = torch.bfloat16,
    device_map: str | dict[str, int] | None = "auto",
) -> None:
    """Carga base + LoRA, fusiona y guarda pesos y tokenizer."""
    logging.info("Cargando modelo base: %s", base_model)
    model = AutoModelForCausalLM.from_pretrained(
        base_model,
        torch_dtype=dtype,
        device_map=device_map,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )

    logging.info("Cargando LoRA: %s", lora_path)
    lora_model = PeftModel.from_pretrained(model, lora_path, device_map=device_map)

    logging.info("Fusionando LoRA en el modelo base...")
    merged = lora_model.merge_and_unload()

    logging.info("Cargando tokenizer desde base: %s", base_model)
    tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    logging.info("Guardando modelo fusionado en: %s", output_dir)
    merged.save_pretrained(output_dir, safe_serialization=True)
    tokenizer.save_pretrained(output_dir)
    logging.info("Listo. Modelo fusionado guardado.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fusiona un LoRA en GPT-OSS 20B y guarda el modelo merged."
    )
    parser.add_argument(
        "--base",
        default="openai/gpt-oss-20b",
        help='ID o ruta del modelo base (default: "openai/gpt-oss-20b")',
    )
    parser.add_argument(
        "--lora",
        default="YiwenX/gpt-oss-20b-multilingual-reasoner",
        help='ID o ruta del LoRA (default: "YiwenX/gpt-oss-20b-multilingual-reasoner")',
    )
    parser.add_argument(
        "--out",
        default="./models/gpt-oss-20b-multireasoner-merged",
        help='Directorio de salida para el modelo fusionado (default: "./models/gpt-oss-20b-multireasoner-merged")',
    )
    parser.add_argument(
        "--dtype",
        default="bfloat16",
        choices=["bfloat16", "float16", "fp16", "float32", "fp32"],
        help="Precisión para cargar y fusionar (default: bfloat16)",
    )
    parser.add_argument(
        "--device-map",
        default="auto",
        help="Asignación de dispositivos para cargar el modelo (default: auto)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    output_dir = Path(args.out)
    dtype = parse_dtype(args.dtype)

    print(
        "Ejecutá este script en un entorno con transformers, peft, accelerate y torch instalados. "
        "El proceso puede consumir mucha RAM/VRAM y tardar varios minutos."
    )

    merge_lora(
        base_model=args.base,
        lora_path=args.lora,
        output_dir=output_dir,
        dtype=dtype,
        device_map=args.device_map,
    )


if __name__ == "__main__":
    main()
