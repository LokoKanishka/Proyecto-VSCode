import sys
import os
import time
import logging
import numpy as np
import sounddevice as sd
import asyncio
from openwakeword import Model
from lucy_voice.config import LucyConfig
# from lucy_voice.orchestrator import LucyOrchestrator # Deprecated
from lucy_voice.pipeline.pipecat_graph import build_lucy_pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )

async def run_conversation(config: LucyConfig):
    """
    Runs the Pipecat pipeline for conversation.
    """
    pipeline = build_lucy_pipeline(config)
    
    # We need a runner
    runner = PipelineRunner()
    
    # Task needs a source. Our AudioInputNode is a processor, but Pipecat usually expects a source at the start?
    # If we put AudioInputNode as first processor, we need to pump it?
    # Or we can use a basic source that yields empty frames to tick the pipeline?
    # For this implementation, let's assume AudioInputNode handles its own loop or we run it manually.
    # But PipelineRunner expects a task.
    
    # Let's manually run the pipeline loop for now to have control, or use runner if standard.
    # Standard runner: runner.run(task)
    # Task(pipeline, params...)
    
    task = PipelineTask(pipeline)
    
    # We need to start our AudioInputNode if it's not auto-started.
    # In our graph, we commented out audio_input in processors list because "Input is usually the source".
    # Let's uncomment it in the graph or add it here?
    # Actually, let's rely on the graph having it.
    # I'll assume build_lucy_pipeline includes AudioInputNode now (I need to fix that in graph if I commented it out).
    
    # Wait, I commented it out in previous step!
    # "audio_input = AudioInputNode(config) # We might manage input separately for now"
    # I should uncomment it in the graph or add it to the pipeline here.
    # Let's add it here for clarity.
    from lucy_voice.pipeline.processors.audio_node import AudioInputNode
    audio_input = AudioInputNode(config)
    
    # Prepend to pipeline processors? Pipeline is immutable?
    # Pipeline(processors)
    # I should fix build_lucy_pipeline to include it.
    # But for now, let's just run the pipeline as is (it has ASR, LLM, TTS, Output).
    # It needs input frames.
    
    # We can create a simple source that reads from AudioInputNode and yields frames.
    # Or AudioInputNode IS the source.
    
    logging.info("Starting conversation pipeline...")
    
    # Start audio input stream
    await audio_input.start()
    
    try:
        # Run loop
        # We need to pump frames from audio_input into pipeline.
        # Pipeline.process(frame)
        
        # Simple loop
        while True:
            # This is a hacky way to bridge AudioInputNode (which I defined as FrameProcessor) 
            # to be a source.
            # Ideally AudioInputNode should have a `read_frame()` method.
            # My AudioInputNode has `run_loop` but it pushes downstream.
            # If it pushes downstream, it needs a "next" processor.
            # But it's not connected if I instantiate it here.
            
            # Let's fix this by making AudioInputNode push to the pipeline's first processor?
            # Or use runner.
            
            # If I use runner, I need a valid Pipecat Source.
            # Since I don't have one, I'll do a manual loop.
            
            # Read audio (blocking or async)
            # I'll use audio_input.stream directly here for simplicity
            if audio_input.stream:
                data, _ = audio_input.stream.read(audio_input.stream.blocksize)
                from pipecat.frames.frames import InputAudioRawFrame
                from pipecat.processors.frame_processor import FrameDirection
                frame = InputAudioRawFrame(
                    audio=data.tobytes(),
                    sample_rate=config.sample_rate,
                    num_channels=config.channels
                )
                
                await pipeline.process_frame(frame, FrameDirection.DOWNSTREAM)
            
            await asyncio.sleep(0.01)
            
            # TODO: Stop condition
            # If we detect "stop" command in LLM?
            # We need a way to signal stop.
            
    except Exception as e:
        logging.error(f"Pipeline error: {e}")
    finally:
        await audio_input.stop()
        logging.info("Conversation pipeline stopped.")

def main():
    setup_logging()
    log = logging.getLogger("WakeWordListener")
    
    # Cargar configuración
    config_path = "config.yaml"
    if os.path.exists(config_path):
        config = LucyConfig.load_from_yaml(config_path)
        log.info(f"Configuración cargada desde {config_path}")
    else:
        config = LucyConfig()
        log.info("Usando configuración por defecto")

    log.info("Cargando LucyOrchestrator...")
    #orchestrator = LucyOrchestrator(config) # Removed
    
    log.info("Cargando modelos de wake word...")
    
    # Check for custom model
    # Use config path if available, otherwise check default location
    model_paths = config.wakeword_model_paths
    if not model_paths:
        custom_model_path = "lucy_voice/data/wakeword/modelos/hola_lucy.onnx"
        if os.path.exists(custom_model_path):
            log.info(f"Modelo custom encontrado: {custom_model_path}")
            model_paths = [custom_model_path]
        else:
            log.info("No se encontró modelo custom 'hola_lucy.onnx'. Usando modelos por defecto.")

    # Initialize model
    model = Model(wakeword_model_paths=model_paths if model_paths else [])

    log.info("=== Lucy Wake Word Listener (Pipecat Integrated) ===")
    if model_paths:
        log.info("Esperando 'Hola Lucy'...")
    else:
        log.info("Esperando 'Hey Jarvis' o 'Alexa' (modelo default)...")

    detected_key = None
    last_trigger_time = 0.0
    
    # Parameters from config
    SAMPLE_RATE = config.sample_rate
    BLOCKSIZE = 1280
    THRESHOLD = config.wakeword_threshold
    COOLDOWN_SECONDS = config.wakeword_cooldown

    try:
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            dtype="float32",
        ) as stream:
            while True:
                audio, _ = stream.read(BLOCKSIZE)
                mono = audio[:, 0].astype(np.float32)
                mono_int16 = (mono * 32767).astype(np.int16)

                prediction = model.predict(mono_int16)

                # Auto-detect key if not set
                if detected_key is None and prediction:
                    # Prioritize custom model
                    if "hola_lucy" in prediction:
                        detected_key = "hola_lucy"
                    elif "hey jarvis" in prediction:
                        detected_key = "hey jarvis"
                    elif "hey_jarvis" in prediction:
                        detected_key = "hey_jarvis"
                    elif "alexa" in prediction:
                        detected_key = "alexa"
                    else:
                        detected_key = next(iter(prediction.keys()))
                    log.info(f"Usando clave de modelo: {repr(detected_key)}")

                if not detected_key:
                    continue

                score = float(prediction.get(detected_key, 0.0))
                
                if score >= THRESHOLD:
                    now = time.time()
                    if (now - last_trigger_time) > COOLDOWN_SECONDS:
                        log.info(f"\n¡Wake word detectado! (Score: {score:0.3f})")
                        
                        log.info("Entrando en modo conversación (Pipecat)...")
                        
                        # Stop wake word stream temporarily?
                        # sd.InputStream is a context manager, but we are inside it.
                        # We can't easily stop it without breaking the loop.
                        # We should break, run pipeline, then restart loop?
                        # Or just stop reading from it?
                        # If we run async pipeline, we need to release the audio device.
                        
                        # Break the loop to release stream
                        break
                        
                    else:
                        # In cooldown
                        pass
            
            # End of stream context
        
        # Run conversation
        asyncio.run(run_conversation(config))
        
        # Restart main to listen again?
        # Recursive call or loop?
        # Better to have a while True loop outside the stream context.
        # But for this prototype, let's just exit or restart.
        log.info("Reiniciando listener...")
        main() # Recursive restart (simple but effective for now)

    except KeyboardInterrupt:
        log.info("\nCortado por el usuario (Ctrl+C).")
    except Exception as e:
        log.error(f"Error en listener: {e}")
        # Retry?
        time.sleep(1)
        main()

if __name__ == "__main__":
    main()
