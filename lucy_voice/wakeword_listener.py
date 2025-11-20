import sys
import os
import time
import logging
import numpy as np
import sounddevice as sd
from openwakeword import Model
from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline

SAMPLE_RATE = 16000
BLOCKSIZE = 1280  # ~80 ms a 16 kHz
THRESHOLD = 0.15
COOLDOWN_SECONDS = 4.0

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )

def main():
    setup_logging()
    log = logging.getLogger("WakeWordListener")
    
    log.info("Cargando LucyVoicePipeline...")
    pipeline = LucyVoicePipeline()
    
    log.info("Cargando modelos de wake word...")
    
    # Check for custom model
    custom_model_path = "lucy_voice/data/wakeword/modelos/hola_lucy.onnx"
    model_paths = []
    if os.path.exists(custom_model_path):
        log.info(f"Modelo custom encontrado: {custom_model_path}")
        model_paths.append(custom_model_path)
    else:
        log.info("No se encontró modelo custom 'hola_lucy.onnx'. Usando modelos por defecto.")

    # Initialize model with custom path if found, otherwise default (empty list loads defaults)
    model = Model(wakeword_model_paths=model_paths if model_paths else [])

    log.info("=== Lucy Wake Word Listener ===")
    if model_paths:
        log.info("Esperando 'Hola Lucy'...")
    else:
        log.info("Esperando 'Hey Jarvis' o 'Alexa' (modelo default)...")

    detected_key = None
    last_trigger_time = 0.0

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
                
                # Optional: print score for debugging (commented out to reduce noise)
                # sys.stdout.write(f"\rScore: {score:0.3f}")
                # sys.stdout.flush()

                if score >= THRESHOLD:
                    now = time.time()
                    if (now - last_trigger_time) > COOLDOWN_SECONDS:
                        log.info(f"\n¡Wake word detectado! (Score: {score:0.3f})")
                        
                        # Trigger Lucy y entrar en modo conversación
                        log.info("Entrando en modo conversación...")
                        
                        # Bucle de conversación continua
                        conversation_active = True
                        turn_count = 0
                        max_no_speech_turns = 2  # Salir después de 2 turnos sin voz
                        no_speech_count = 0
                        
                        while conversation_active:
                            turn_count += 1
                            log.info(f"--- Turno {turn_count} ---")
                            
                            # Ejecutar un turno de conversación
                            result = pipeline.run_mic_llm_roundtrip_once(use_vad=True)
                            
                            if result == "stop":
                                log.info("Usuario solicitó desactivación.")
                                conversation_active = False
                            elif result == "no_speech":
                                no_speech_count += 1
                                log.info(f"Sin voz detectada ({no_speech_count}/{max_no_speech_turns})")
                                if no_speech_count >= max_no_speech_turns:
                                    log.info("Saliendo por inactividad.")
                                    conversation_active = False
                            else:  # "continue"
                                no_speech_count = 0  # Reset contador
                        
                        log.info("Volviendo a escuchar wake word...")
                        last_trigger_time = time.time()
                        model.reset()
                    else:
                        # In cooldown
                        pass

    except KeyboardInterrupt:
        log.info("\nCortado por el usuario (Ctrl+C).")

if __name__ == "__main__":
    main()
