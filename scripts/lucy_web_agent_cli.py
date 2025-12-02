#!/usr/bin/env python
"""
CLI para el Lucy Web Agent (DDGS + Ollama local).

Ejemplo de uso:

    ./scripts/lucy_web_agent.sh "Buscá noticias recientes sobre la economía argentina y resumilas..."

"""

from __future__ import annotations

import argparse
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from lucy_agents.web_agent import run_web_research, DEFAULT_OLLAMA_MODEL_ID  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lucy Web Agent (DDGS + modelo local de Ollama)."
    )
    parser.add_argument(
        "task",
        nargs="+",
        help="Consulta o tarea de investigación en lenguaje natural.",
    )
    parser.add_argument(
        "--model-id",
        default=None,
        help=(
            "ID del modelo en Ollama (por ejemplo gpt-oss:20b). "
            f"Por defecto: {DEFAULT_OLLAMA_MODEL_ID}."
        ),
    )
    parser.add_argument(
        "--max-results",
        type=int,
        default=8,
        help="Cantidad máxima de resultados web (default: 8).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Aumenta verbosidad (-v, -vv).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    task = " ".join(args.task)

    model_label = args.model_id or DEFAULT_OLLAMA_MODEL_ID

    print(
        "╭──────────────── Lucy Web Agent ────────────────╮"
    )
    print(f"│  Modelo: {model_label:<33}│")
    print(f"│  Resultados DDGS: {args.max_results:<23}│")
    print("╰────────────────────────────────────────────────╯\n")

    print("Tarea:", task)
    print()

    try:
        answer = run_web_research(
            task=task,
            model_id=args.model_id,
            max_results=args.max_results,
            verbosity=args.verbose,
        )
    except Exception as exc:  # pragma: no cover - salida de error sencilla
        print("\n[Lucy web-agent] Error al ejecutar la tarea:\n")
        print(repr(exc))
        sys.exit(1)

    print("──────── Respuesta de Lucy Web ────────\n")
    print(answer)
    print("\n───────────────────────────────────────\n")


if __name__ == "__main__":
    main()
