from __future__ import annotations

from typing import Any, Optional
from loguru import logger

try:
    from pipecat.pipeline.pipeline import Pipeline
except ImportError as e:
    Pipeline = None
    _pipecat_import_error = e

from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.processors.asr_node import WhisperASRProcessor
from lucy_voice.pipeline.processors.llm_node import OllamaLLMProcessor
from lucy_voice.pipeline.processors.tts_node import MimicTTSProcessor
from lucy_voice.pipeline.processors.audio_node import AudioInputNode, AudioOutputNode

def build_lucy_pipeline(config: Optional[LucyConfig] = None) -> "Pipeline":
    if Pipeline is None:
        logger.error("[LucyPipecatGraph] Pipecat import error: {}", _pipecat_import_error)
        raise RuntimeError("Pipecat not installed.")

    if config is None:
        config = LucyConfig()

    logger.info("Building Lucy Pipecat Pipeline...")

    # Create processors
    # audio_input = AudioInputNode(config) # We might manage input separately for now
    asr = WhisperASRProcessor(config)
    llm = OllamaLLMProcessor(config)
    tts = MimicTTSProcessor(config)
    audio_output = AudioOutputNode(config)

    processors = [
        # audio_input, # Input is usually the source, handled by runner
        asr,
        llm,
        tts,
        audio_output
    ]

    pipeline = Pipeline(processors)
    logger.info("Pipeline created.")
    return pipeline
