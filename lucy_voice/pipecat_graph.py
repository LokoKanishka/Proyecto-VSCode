"""
pipecat_graph.py

Primer esqueleto del grafo "real" de Pipecat para Lucy.

Ahora devuelve un Pipeline que ya incluye un procesador de texto
conectado al LLM local (Ollama), aunque todavía no lo estemos usando
desde los modos actuales (texto/PTT/wake word).
"""

from __future__ import annotations

from typing import Any, Optional
from loguru import logger

try:
    # Import básico de Pipecat. Si no está instalado, dejamos un mensaje claro.
    from pipecat.pipeline.pipeline import Pipeline
except ImportError as e:  # pragma: no cover
    Pipeline = None  # type: ignore
    _pipecat_import_error = e
else:
    _pipecat_import_error = None

from lucy_voice.pipecat_processors import LucyOllamaTextLLMProcessor


def build_lucy_pipeline(config: Optional[Any] = None) -> "Pipeline":
    """
    Fábrica del Pipeline de Lucy.

    En esta versión todavía no conectamos micrófono, ASR ni TTS dentro
    del grafo. Pero ya:

    - Verificamos que Pipecat esté correctamente importado.
    - Creamos un procesador de texto → LLM local (Ollama).
    - Lo incluimos en la lista de procesadores del Pipeline.

    Aceptamos un objeto de configuración `config` (LucyPipelineConfig),
    del cual por ahora usamos sólo `llm_model`.
    """
    if Pipeline is None:
        # Pipecat no se pudo importar: dejamos un error explícito.
        logger.error(
            "[LucyPipecatGraph] No se pudo importar Pipecat: {}",
            _pipecat_import_error,
        )
        raise RuntimeError(
            "Pipecat no está disponible en este entorno. "
            "Asegurate de tener instalado 'pipecat-ai' en el venv de Lucy Voz."
        )

    # Elegimos el modelo a partir de la config de Lucy, con default.
    model_name = getattr(config, "llm_model", "gpt-oss:20b")

    # Más adelante, esta lista va a contener todos los procesadores reales:
    #   - micrófono / input
    #   - ASR (faster-whisper)
    #   - LLM local (Ollama)
    #   - TTS (Mimic 3)
    #
    # Por ahora arrancamos con el procesador de texto → LLM local.
    processors: list[Any] = [
        LucyOllamaTextLLMProcessor(model=model_name),
    ]

    logger.info(
        "[LucyPipecatGraph] build_lucy_pipeline(): creando Pipeline base "
        "para Lucy (con procesador LLM LucyOllamaTextLLMProcessor, modelo = {})",
        model_name,
    )

    pipeline = Pipeline(processors)

    logger.info(
        "[LucyPipecatGraph] build_lucy_pipeline(): Pipeline creado: {}",
        pipeline,
    )

    return pipeline
