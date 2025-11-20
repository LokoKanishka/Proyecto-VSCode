"""
pipecat_text_demo.py

Demo minima para probar el grafo de Pipecat de Lucy usando solo texto.

Hace esto:
- Crea un LucyVoicePipeline con la config por defecto.
- Construye el grafo Pipecat (que ya incluye LLM + salida a consola).
- Corre un PipelineTask que procesa un TextFrame con un saludo de prueba.
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
    """
    Punto de entrada async de la demo.
    """
    logger.info("[LucyPipecatDemo] Iniciando demo de texto con Pipecat…")

    # 1) Creamos la config y el orquestador de alto nivel de Lucy
    config = LucyPipelineConfig()
    lucy = LucyVoicePipeline(config=config)

    # 2) Construimos el grafo Pipecat y recuperamos el Pipeline interno
    lucy.build_graph()
    pipeline: Any = lucy._graph  # type: ignore[attr-defined]

    if pipeline is None:
        raise RuntimeError(
            "[LucyPipecatDemo] El grafo de Pipecat no se construyó correctamente."
        )

    # 3) Armamos el runner y el task de Pipecat
    runner = PipelineRunner()
    task = PipelineTask(pipeline)

    # 4) Encolamos un TextFrame de prueba + EndFrame para cerrar el pipeline
    saludo = "Hola Lucy, probemos el pipeline de texto por Pipecat."
    logger.info("[LucyPipecatDemo] Encolando TextFrame de saludo: {}", saludo)

    await task.queue_frames(
        [
            TextFrame(saludo),
            EndFrame(),
        ]
    )

    # 5) Ejecutamos el pipeline
    logger.info("[LucyPipecatDemo] Ejecutando runner.run(task)…")
    await runner.run(task)
    logger.info("[LucyPipecatDemo] Demo de texto con Pipecat terminada.")


if __name__ == "__main__":
    asyncio.run(main())

