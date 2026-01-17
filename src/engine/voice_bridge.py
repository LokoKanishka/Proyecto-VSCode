import threading
import subprocess
import logging
import numpy as np
import sounddevice as sd
import scipy.io.wavfile as wav
import os

# Configuración
SAMPLE_RATE = 16000
TTS_VOICE = "es_ES/m-ailabs_low#karen_savage"

class LucyVoiceBridge:
    def __init__(self):
        self.logger = logging.getLogger("LucyBridge")
        self.asr_model = None
        
        try:
            from faster_whisper import WhisperModel
            print("⬇️ [Engine] Cargando modelo Whisper...")
            self.asr_model = WhisperModel("small", device="cpu", compute_type="int8")
            print("✅ [Engine] Oído listo.")
        except Exception as e:
            print(f"❌ [Engine] Error cargando Whisper: {e}")

    def listen_oneshot(self, callback_text, callback_finished):
        if not self.asr_model:
            print("❌ [Engine] No puedo escuchar (Whisper no cargó).")
            callback_finished()
            return

        print("\n🎤 [Engine] GRABANDO (5s)... ¡HABLA AHORA!")
        
        try:
            duration = 5.0
            # Grabar
            recording = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()
            
            # --- CORRECCIÓN CRÍTICA: APLANAR EL ARRAY ---
            # sounddevice devuelve (80000, 1), Whisper quiere (80000,)
            recording = recording.flatten()
            
            # --- GUARDAR DEBUG PARA VERIFICAR ---
            # Guardamos lo que escuchó para que puedas reproducirlo si falla
            wav.write("debug_audio.wav", SAMPLE_RATE, recording)
            print("💾 [Engine] Audio guardado en 'debug_audio.wav' para análisis.")

            # Chequeo de volumen
            vol = np.linalg.norm(recording) * 10
            print(f"📊 [Engine] Volumen detectado: {vol:.2f}")

            if vol < 1.0:
                print("⚠️ [Engine] Silencio detectado. Ignorando.")
                callback_finished()
                return

            # Transcribir
            print("🧠 [Engine] Transcribiendo...")
            segments, info = self.asr_model.transcribe(recording, beam_size=5, language="es")
            text = " ".join([segment.text for segment in segments]).strip()
            
            print(f"📝 [Engine] Texto detectado: '{text}'")
            
            if text:
                callback_text(text)
            
        except Exception as e:
            print(f"❌ [Engine] Error crítico: {e}")
        finally:
            print("🔴 [Engine] Fin del ciclo.")
            callback_finished()

    def say(self, text):
        if not text: return
        visible_text = text.replace("Thinking...", "").strip()
        threading.Thread(target=self._speak_thread, args=(visible_text,)).start()

    def _speak_thread(self, text):
        print(f"🔊 [Boca] Diciendo: {text[:30]}...")
        try:
            cmd_mimic = ["mimic3", "--voice", TTS_VOICE, "--stdout"]
            p1 = subprocess.Popen(cmd_mimic, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
            p2 = subprocess.Popen(["aplay"], stdin=p1.stdout)
            p1.communicate(input=text.encode('utf-8'))
            p2.wait()
        except Exception as e:
            print(f"❌ [Boca] Error: {e}")
