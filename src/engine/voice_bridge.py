import threading
import subprocess
import numpy as np
import sounddevice as sd
import os
import time

# --- CONFIGURACIÓN ELÁSTICA ---
SAMPLE_RATE = 16000
DIGITAL_GAIN = 5.0
SILENCE_THRESHOLD = 0.6
SILENCE_TIMEOUT = 2.0  # Espera 2 segundos de silencio antes de cortar
MAX_RECORD_TIME = 30   # Te deja hablar hasta 30 segundos

class LucyVoiceBridge:
    def __init__(self, audio_processor=None):
        self.asr_model = None
        self.should_record = False
        try:
            from faster_whisper import WhisperModel
            print("⬇️ [Engine] Cargando Whisper 'small'...")
            self.asr_model = WhisperModel("small", device="cpu", compute_type="int8")
            print("✅ [Engine] OÍDO LISTO.")
        except Exception as e:
            print(f"❌ [Engine] Error Carga: {e}")

    def stop_listening(self):
        self.should_record = False

    def listen_once(self, callback_text):
        if not self.asr_model: return
        self.should_record = True
        print(f"🟢 [Mic] ESCUCHANDO... (Habla tranquilo)")
        
        full_audio = []
        start_time = time.time()
        last_sound_time = time.time()
        
        while self.should_record:
            try:
                chunk = sd.rec(int(0.2 * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
                sd.wait()
            except: break
            
            chunk = chunk.flatten() * DIGITAL_GAIN
            vol = np.linalg.norm(chunk) * 10
            
            # Si hay voz, reseteamos el reloj de silencio
            if vol > SILENCE_THRESHOLD:
                last_sound_time = time.time()
                print(f"   🎤 Voz detectada ({vol:.1f})...", end="\r")
            
            full_audio.append(chunk)
            
            # Condición 1: Silencio prolongado
            if time.time() - last_sound_time > SILENCE_TIMEOUT and len(full_audio) > 10:
                print("\n✂️ Silencio detectado. Procesando...")
                break
                
            # Condición 2: Tiempo máximo
            if time.time() - start_time > MAX_RECORD_TIME:
                print("\n⚠️ Tiempo límite.")
                break
        
        if not full_audio: return

        audio_data = np.concatenate(full_audio)
        if np.max(np.abs(audio_data)) < 0.1: return

        max_val = np.max(np.abs(audio_data))
        if max_val > 0: audio_data = audio_data / max_val

        try:
            # Transcribir
            segments, info = self.asr_model.transcribe(
                audio_data, beam_size=5, language="es", condition_on_previous_text=False,
                initial_prompt="Conversación en español, transcripción completa."
            )
            text = " ".join([segment.text for segment in segments]).strip()
            
            # Filtro Anti-Basura
            ignored = ["thank you", "hello", "you", "subtitles"]
            if text.lower() in ignored or len(text) < 2:
                print(f"🗑️ Ignorado: {text}")
                return
                
            print(f"📝 [Transcripción] '{text}'")
            if text: callback_text(text)

        except Exception as e:
            print(f"❌ Error: {e}")

    def say(self, text):
        if not text: return
        threading.Thread(target=self._speak_thread, args=(text,)).start()

    def _speak_thread(self, text):
        wav_file = os.path.abspath("response.wav")
        try:
            subprocess.run(["mimic3", "--voice", "es_ES/m-ailabs_low#karen_savage", text], stdout=open(wav_file, "wb"))
            if os.path.exists(wav_file):
                # Usamos paplay según sugerencia previa
                subprocess.run(["paplay", wav_file])
        except: pass
