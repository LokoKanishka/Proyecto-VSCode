#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import os
import sys
from textwrap import dedent

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from lucy_agents.web_agent import run_web_research, DEFAULT_OLLAMA_MODEL_ID


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lucy_web_agent",
        description="Agente de búsqueda web de Lucy (DuckDuckGo + Ollama).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=dedent(
            """Ejemplos:
  lucy_web_agent_cli.py "Buscá noticias recientes sobre la economía argentina..."
  lucy_web_agent_cli.py -m gpt-oss:20b "Qué está pasando con el cambio climático en 2025?"
"""
        ),
    )
    parser.add_argument(
        "task",
        help="Consigna completa en español (qué querés que investigue y resuma Lucy).",
    )
    parser.add_argument(
        "-m",
        "--model-id",
        default=os.getenv("LUCY_WEB_AGENT_MODEL", DEFAULT_OLLAMA_MODEL_ID),
        help=f"Modelo de Ollama a usar (por defecto: {DEFAULT_OLLAMA_MODEL_ID}).",
    )
    parser.add_argument(
        "-k",
        "--max-results",
        type=int,
        default=8,
        help="Cantidad de resultados de DuckDuckGo a considerar (por defecto: 8).",
    )

    args = parser.parse_args()

    print("")
    print("╭──────────────── Lucy Web Agent ────────────────╮")
    print(f"│  Modelo: {args.model_id:<37} │")
    print(f"│  Resultados DuckDuckGo: {args.max_results:<21} │")
    print("╰────────────────────────────────────────────────╯")
    print("")
    print(f"Tarea: {args.task}")
    print("")

    answer = run_web_research(
        task=args.task,
        model_id=args.model_id,
        max_results=args.max_results,
    )

    print("\n──────── Respuesta de Lucy Web ────────\n")
    print(answer)
    print("\n───────────────────────────────────────\n")


if __name__ == "__main__":
    main()
