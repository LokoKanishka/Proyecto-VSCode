"""
pipecat_graph.py

Primer esqueleto del grafo "real" de Pipecat para Lucy.

Devuelve un Pipeline que incluye:
- un procesador de texto que llama al LLM local (Ollama);
- un procesador que imprime los TextFrame en consola;
aunque todavia no usemos este grafo desde los modos actuales
(texto / PTT / wake word).
"""

from __future__ import annotations

from typing import Any, Optional
from loguru import logger

try:
    # Import basico de Pipecat. Si no esta instalado, dejamos un mensaje claro.
    from pipecat.pipeline.pipeline import Pipeline
except ImportError as e:  # pragma: no cover
    Pipeline = None  # type: ignore
    _pipecat_import_error = e
else:
    _pipecat_import_error = None

from lucy_voice.pipecat_processors import (
    LucyOllamaTextLLMProcessor,
    LucyConsoleTextOutputProcessor,
)


def build_lucy_pipeline(config: Optional[Any] = None) -> "Pipeline":
    """
    Fabrica del Pipeline de Lucy.

    En esta version todavia no conectamos microfono, ASR ni TTS dentro
    del grafo. Pero ya:

    - verificamos que Pipecat se importe correctamente;
    - creamos un procesador de texto a LLM local (Ollama);
    - agregamos un procesador que imprime los TextFrame en consola.

    Aceptamos un objeto de configuracion `config` (LucyPipelineConfig),
    del cual por ahora usamos solo `llm_model`.
    """
    if Pipeline is None:
        # Pipecat no se pudo importar: dejamos un error explicito.
        logger.error(
            "[LucyPipecatGraph] No se pudo importar Pipecat: {}",
            _pipecat_import_error,
        )
        raise RuntimeError(
            "Pipecat no esta disponible en este entorno. "
            "Asegurate de tener instalado 'pipecat-ai' en el venv de Lucy Voz."
        )

    # Elegimos el modelo a partir de la config de Lucy, con valor por defecto.
    model_name = getattr(config, "llm_model", "gpt-oss:20b")

    processors: list[Any] = [
        LucyOllamaTextLLMProcessor(model=model_name),
        LucyConsoleTextOutputProcessor(prefix="[LucyPipecat-TextOut]"),
    ]

    logger.info(
        "[LucyPipecatGraph] build_lucy_pipeline(): creando Pipeline base "
        "para Lucy (modelo LLM = {})",
        model_name,
    )

    pipeline = Pipeline(processors)

    logger.info(
        "[LucyPipecatGraph] build_lucy_pipeline(): Pipeline creado: {}",
        pipeline,
    )

    return pipeline
