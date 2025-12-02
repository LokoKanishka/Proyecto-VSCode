#!/usr/bin/env python
"""CLI simple para usar el agente web de Lucy desde la terminal.

Ejemplos:

    python scripts/lucy_web_agent_cli.py "Buscá noticias de hoy sobre la economía argentina"
    python scripts/lucy_web_agent_cli.py --verbose "Compará las RTX 5090 con las 4090 para gaming"

También se puede usar sin argumentos; en ese caso pide la tarea por stdin.
"""

import argparse
import textwrap

from lucy_agents.web_agent import run_web_research, DEFAULT_OLLAMA_MODEL_ID


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="lucy_web_agent_cli",
        description="Agente de investigación web de Lucy (smolagents + Ollama + DuckDuckGo).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent(
            """\
            Tip:
              - Asegurate de tener Ollama corriendo y el modelo `gpt-oss:20b`
                descargado (ollama pull gpt-oss:20b).
              - Este script NO usa ninguna API de pago: todo el modelo corre local.
            """
        ),
    )
    parser.add_argument(
        "task",
        nargs="*",
        help="Tarea o pregunta a investigar (si se deja vacío, se pide por stdin).",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_OLLAMA_MODEL_ID,
        help=(
            "ID del modelo para LiteLLM. "
            "Por defecto usa un modelo local de Ollama: %(default)s"
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Muestra más información de depuración del agente.",
    )

    args = parser.parse_args()
    task = " ".join(args.task).strip()

    if not task:
        task = input("Escribí la tarea para el agente web de Lucy: ").strip()
        if not task:
            raise SystemExit("No se recibió ninguna tarea. Abortando.")

    verbosity = 2 if args.verbose else 1

    print("\n[Lucy Web] Ejecutando agente de investigación...\n")
    answer = run_web_research(
        task=task,
        model_id=args.model_id,
        verbosity=verbosity,
    )

    print("\n====== Respuesta del agente web de Lucy ======\n")
    print(answer)
    print("\n==============================================\n")


if __name__ == "__main__":
    main()
