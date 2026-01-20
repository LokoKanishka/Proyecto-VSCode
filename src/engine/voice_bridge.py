import threading
import subprocess
import numpy as np
import os
import time

class LucyVoiceBridge:
    def __init__(self, audio_processor=None):
        self.asr_model = None
        self.is_listening_loop = False
        self.is_speaking = False
        self.processor = audio_processor
        
        # Localizar mimic3
        self.mimic_bin = "mimic3"
        probable_paths = [
            "/home/xdie/Proyecto-VSCode/.venv/bin/mimic3",
            os.path.expanduser("~/.local/bin/mimic3")
        ]
        for p in probable_paths:
            if os.path.exists(p):
                self.mimic_bin = p
                break
        
        try:
            from faster_whisper import WhisperModel
            print("⬇️ [Engine] Iniciando Whisper (Strict Unified Mode)...")
            self.asr_model = WhisperModel("Systran/faster-distil-whisper-large-v3", device="cpu", compute_type="int8")
            print(f"✅ [Engine] OÍDO UNIFICADO LISTO")
        except Exception as e:
            print(f"❌ [Engine] Error Carga STT: {e}")

    def stop_listening(self):
        self.is_listening_loop = False

    def start_listening_loop(self, callback_text):
        """Consume audio from shared processor and transcribe snippet by snippet."""
        if not self.asr_model or not self.processor: 
            print("❌ [VoiceBridge] Falta Processor o Modelo.")
            return
        
        self.is_listening_loop = True
        print("🟢 [Bridge] Escucha Activa unificada.")

        while self.is_listening_loop:
            if self.is_speaking:
                time.sleep(0.5)
                continue

            try:
                # Detección de nivel (VAD) desde el procesador central
                level = self.processor.get_rms_level() * 10 # Escalar para que sea legible como el test_ear del usuario
                
                # Debug log de volumen (cada 0.6 seg aprox)
                print(f"   📊 Nivel Audio: {level:.2f} (Umbral: 0.50)")
                
                if level > 0.50: # Umbral propuesto por el usuario (SILENCE_THRESHOLD)
                    print(f"🎤 Voz captada ({level:.3f})... Analizando.")
                    
                    # Gap de captura para frases completas
                    time.sleep(1.8)
                    
                    # Consumimos audio del buffer compartido (AudioProcessor)
                    audio_data = self.processor.consume_buffer()
                    
                    if len(audio_data) < 4000:
                        continue
                        
                    # Transcribir Estrictamente en Español
                    segments, _ = self.asr_model.transcribe(
                        audio_data, 
                        language="es",
                        task="transcribe",
                        initial_prompt="Asistente Lucy conversando en español neutro.",
                        condition_on_previous_text=False,
                        no_speech_threshold=0.6,
                        log_prob_threshold=-1.0
                    )
                    
                    text = " ".join([s.text for s in segments]).strip()
                    print(f"📝 [STT] {text}")
                    
                    # Filtro de alucinaciones (Suscríbete, etc.)
                    blacklist = ["Suscríbete", "Subtítulos", "Amara.org", "Thank you", "gracias por ver", "Muchas gracias"]
                    if text and not any(x.lower() in text.lower() for x in blacklist):
                        if len(text) > 1:
                            callback_text(text)
                            time.sleep(1)
                else:
                    time.sleep(0.3)

            except Exception as e:
                print(f"❌ Error en Bridge: {e}")
                time.sleep(1)

    def say(self, text):
        if not text: return
        self.is_speaking = True
        threading.Thread(target=self._speak_thread, args=(text,)).start()

    def _speak_thread(self, text):
        wav_file = os.path.abspath("response.wav")
        try:
            subprocess.run([self.mimic_bin, "--voice", "es_ES/m-ailabs_low#karen_savage", text], stdout=open(wav_file, "wb"))
            if os.path.exists(wav_file):
                print(f"🔊 [Lucy] Hablando...")
                # Usamos aplay o paplay según disponibilidad
                subprocess.run(["aplay", wav_file])
        except Exception as e:
            print(f"❌ Error Audio: {e}")
        finally:
            self.is_speaking = False
