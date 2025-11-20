"""
pipecat_text_repl.py

REPL sencillo de texto usando el grafo Pipecat de Lucy.

- Construye una LucyVoicePipeline con LucyPipelineConfig por defecto.
- Arma el Pipeline de Pipecat (que ya incluye LLM + salida a consola).
- Entra en un loop donde:
    Vos: escribís texto
    Lucy: responde a través del pipeline (LucyOllamaTextLLMProcessor
          + LucyConsoleTextOutputProcessor)
- Escribí 'salir' para terminar.
"""

from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from pipecat.frames.frames import TextFrame, EndFrame
from pipecat.pipeline.task import PipelineTask
from pipecat.pipeline.runner import PipelineRunner

from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline, LucyPipelineConfig


async def main() -> None:
    logger.info("[LucyPipecatREPL] Iniciando REPL de texto con Pipecat…")

    # 1) Config y orquestador de Lucy
    config = LucyPipelineConfig()
    lucy = LucyVoicePipeline(config=config)

    # 2) Construimos el grafo Pipecat
    lucy.build_graph()
    pipeline: Any = lucy._graph  # type: ignore[attr-defined]

    if pipeline is None:
        raise RuntimeError(
            "[LucyPipecatREPL] El grafo de Pipecat no se construyó correctamente."
        )

    # 3) Runner que va a ejecutar los tasks sobre el pipeline
    runner = PipelineRunner()

    print("Lucy voz (REPL Pipecat). Escribí 'salir' para terminar.\n")

    # 4) Loop de conversación
    while True:
        try:
            user_text = input("Vos: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[LucyPipecatREPL] Saliendo por interrupción. Chau 💜")
            break

        if not user_text:
            continue

        if user_text.lower() == "salir":
            print("[LucyPipecatREPL] Chau, hasta luego 💜")
            break

        # Armamos un task para este turno
        task = PipelineTask(pipeline)

        # Encolamos el texto del usuario + EndFrame para cerrar el flujo
        await task.queue_frames(
            [
                TextFrame(user_text),
                EndFrame(),
            ]
        )

        # Ejecutamos el pipeline para este turno
        logger.info(
            "[LucyPipecatREPL] Ejecutando runner.run(task) para texto: {}",
            user_text,
        )
        await runner.run(task)


if __name__ == "__main__":
    asyncio.run(main())
