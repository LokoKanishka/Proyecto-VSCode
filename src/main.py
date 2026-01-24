import os
import sys
import logging
import time
import speech_recognition as sr
import pyttsx3
from faster_whisper import WhisperModel
from src.engine.ollama_engine import process_intent

# --- CONFIGURACIÓN WINDOWS ---
# Ajuste automático: Si hay CUDA (NVIDIA) úsalo, si no, CPU.
try:
    import torch
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
except ImportError:
    DEVICE = "cpu"

MODEL_SIZE = "medium"
COMPUTE_TYPE = "float16" if DEVICE == "cuda" else "int8"

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("LucyOS")

class LucyBody:
    def __init__(self):
        logger.info(f" 🟢 Inicializando Lucy en Windows (Device: {DEVICE})...")
        
        # 1. Motor de Voz (Nativo Windows)
        try:
            self.engine = pyttsx3.init()
            # Seleccionar voz en español si existe
            voices = self.engine.getProperty('voices')
            for v in voices:
                if "spanish" in v.name.lower() or "es-" in v.id.lower():
                    self.engine.setProperty('voice', v.id)
                    break
            self.engine.setProperty('rate', 150) # Velocidad un poco más rápida
        except Exception as e:
            logger.error(f"Error iniciando TTS: {e}")
            sys.exit(1)
        
        # 2. Cargar Oído (Whisper)
        try:
            logger.info(f"👂 Cargando Whisper {MODEL_SIZE}...")
            self.ear = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        except Exception as e:
            logger.error(f"❌ Error Whisper: {e}")
            logger.info("Intentando fallback a CPU int8...")
            self.ear = WhisperModel("tiny", device="cpu", compute_type="int8")

        # 3. Micrófono
        self.recognizer = sr.Recognizer()

    def listen(self):
        with sr.Microphone() as source:
            logger.info("🎤 Escuchando... (Hable ahora)")
            try:
                # Ajuste rápido de ruido
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                
                # Guardar temporal
                with open("temp_audio.wav", "wb") as f:
                    f.write(audio.get_wav_data())
                return "temp_audio.wav"
            except sr.WaitTimeoutError:
                return None
            except Exception as e:
                logger.error(f"Error Mic: {e}")
                return None

    def transcribe(self, audio_path):
        if not audio_path: return ""
        try:
            segments, _ = self.ear.transcribe(audio_path, beam_size=5)
            text = " ".join([segment.text for segment in segments]).strip()
            if text: logger.info(f"👂 Oído: '{text}'")
            return text
        except Exception as e:
            logger.error(f"Error Transcripción: {e}")
            return ""

    def speak(self, text):
        if not text: return
        logger.info(f"🗣️ Lucy: {text}")
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            logger.error(f"Error Voz: {e}")

    def run(self):
        logger.info("🚀 SISTEMA ONLINE. Di 'Hola Lucy'.")
        while True:
            try:
                audio = self.listen()
                if audio:
                    text = self.transcribe(audio)
                    if len(text) > 2:
                        # Procesar con el Cerebro Monolítico
                        response = process_intent(text)
                        self.speak(response)
            except KeyboardInterrupt:
                logger.info("Apagando...")
                break

if __name__ == "__main__":
    lucy = LucyBody()
    lucy.run()
