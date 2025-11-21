import sys
import os
import logging
import asyncio
from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.pipecat_graph import build_lucy_pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )

async def run_pipeline(config: LucyConfig):
    """
    Runs the Pipecat pipeline for continuous conversation.
    """
    pipeline = build_lucy_pipeline(config)
    
    logging.info("Starting Lucy Voice Pipeline (WakeWord -> VAD -> ASR -> LLM -> TTS)")
    
    # Create task and runner
    task = PipelineTask(pipeline)
    runner = PipelineRunner()
    
    try:
        # Run the pipeline - this will handle StartFrame/EndFrame automatically
        await runner.run(task)
    except asyncio.CancelledError:
        logging.info("Pipeline cancelled.")
    except Exception as e:
        logging.error(f"Pipeline error: {e}")
        raise

def main():
    setup_logging()
    log = logging.getLogger("LucyListener")
    
    # Load config
    config_path = "config.yaml"
    if os.path.exists(config_path):
        config = LucyConfig.load_from_yaml(config_path)
        log.info(f"Config loaded from {config_path}")
    else:
        config = LucyConfig()
        log.info("Using default config")

    try:
        asyncio.run(run_pipeline(config))
    except KeyboardInterrupt:
        log.info("\nStopped by user (Ctrl+C).")
    except Exception as e:
        log.error(f"Error in main: {e}")
        raise

if __name__ == "__main__":
    main()


