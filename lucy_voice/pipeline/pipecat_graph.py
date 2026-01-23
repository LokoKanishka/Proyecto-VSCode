from __future__ import annotations

from typing import Any, Optional
from loguru import logger

try:
    from pipecat.pipeline.pipeline import Pipeline
except ImportError as e:
    Pipeline = None
    _pipecat_import_error = e

from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.processors.audio_node import AudioInputNode, AudioOutputNode
from lucy_voice.pipeline.processors.wakeword_node import WakeWordNode
from lucy_voice.pipeline.processors.vad_node import VADNode
from lucy_voice.pipeline.processors.asr_node import WhisperASRProcessor
from lucy_voice.pipeline.processors.llm_node import OllamaLLMProcessor
from lucy_voice.pipeline.processors.tts_node import MimicTTSProcessor

def build_lucy_pipeline(config: Optional[LucyConfig] = None) -> "Pipeline":
    if Pipeline is None:
        logger.error("[LucyPipecatGraph] Pipecat import error: {}", _pipecat_import_error)
        raise RuntimeError("Pipecat not installed.")

    if config is None:
        config = LucyConfig()

    logger.info("Building Lucy Pipecat Pipeline...")

    # Create processors
    # Input
    audio_input = AudioInputNode(config)
    
    # Filtering / Detection
    wakeword = WakeWordNode(config)
    vad = VADNode(config)
    
    # Processing
    asr = WhisperASRProcessor(config)
    llm = OllamaLLMProcessor(config)
    tts = MimicTTSProcessor(config)
    
    # Output
    # Wire callback to reset wakeword node after playback
    audio_output = AudioOutputNode(config, on_complete=wakeword.reset)


    processors = [
        audio_input,
        wakeword,
        vad,
        asr,
        llm,
        tts,
        audio_output
    ]

    pipeline = Pipeline(processors)
    logger.info("Pipeline created.")
    return pipeline

