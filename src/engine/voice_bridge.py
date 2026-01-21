import threading
import subprocess
import numpy as np
import sounddevice as sd
import os
import time
import queue
import wave

# CONFIGURACIÓN DEBUG
SAMPLE_RATE = 16000
DIGITAL_GAIN = 3.0      # Subimos un poco la ganancia por si hablas bajo
SILENCE_THRESHOLD = 0.3
SILENCE_TIMEOUT = 2.0
MAX_RECORD_TIME = 30

class LucyVoiceBridge:
    def __init__(self):
        self.asr_model = None
        self.should_record = False
        self.is_speaking = False
        self.audio_queue = queue.Queue()
        
        try:
            from faster_whisper import WhisperModel
            print("⬇️ [Engine] Cargando Whisper 'small'...")
            self.asr_model = WhisperModel("small", device="cpu", compute_type="int8")
            print("✅ [Engine] OÍDO LISTO.")
        except Exception as e:
            print(f"❌ [Engine] Error Carga: {e}")

    def stop_listening(self):
        self.should_record = False

    def audio_callback(self, indata, frames, time, status):
        if self.should_record and not self.is_speaking:
            self.audio_queue.put(indata.copy())

    def listen_continuous(self):
        if not self.asr_model: return None
        
        self.should_record = True
        print(f"🟢 [Mic] ESCUCHANDO... (Habla fuerte)")
        
        while not self.audio_queue.empty(): self.audio_queue.get()

        full_audio = []
        start_time = time.time()
        last_sound_time = time.time()
        speech_started = False
        frames_captured = 0
        
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=self.audio_callback, blocksize=4000):
            while self.should_record:
                if self.is_speaking:
                    time.sleep(0.1)
                    start_time = time.time()
                    last_sound_time = time.time()
                    continue

                try:
                    chunk = self.audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                
                chunk = chunk.flatten() * DIGITAL_GAIN
                vol = np.linalg.norm(chunk) * 10
                
                if vol > SILENCE_THRESHOLD:
                    if not speech_started:
                        speech_started = True
                        print(f"   🎤 Voz detectada (Vol: {vol:.1f})...", end="\r")
                    last_sound_time = time.time()
                
                if speech_started:
                    full_audio.append(chunk)
                    frames_captured += 1
                
                # Cortar si hubo silencio después de hablar
                if speech_started and (time.time() - last_sound_time > SILENCE_TIMEOUT):
                    print("\n✋ Silencio final detectado.")
                    break
                
                if time.time() - start_time > MAX_RECORD_TIME:
                    print("\n⚠️ Tiempo máximo.")
                    break

        if not full_audio or len(full_audio) < 5: 
            return None # Fue solo un clic o ruido muy corto
        
        print(f"🧠 Procesando {len(full_audio)} fragmentos...")
        audio_data = np.concatenate(full_audio)
        max_val = np.max(np.abs(audio_data))
        if max_val > 0: audio_data = audio_data / max_val

        try:
            segments, info = self.asr_model.transcribe(
                audio_data, beam_size=5, language="es", condition_on_previous_text=False,
                initial_prompt="Diálogo en español."
            )
            text = " ".join([segment.text for segment in segments]).strip()
            
            # --- ZONA DE DEPURACIÓN ---
            print(f"🔍 [OÍDO RAW] '{text}'") # Muestra TODO lo que escucha
            
            ignored = ["thank you", "subtitles", "you", "copyright"]
            if text.lower() in ignored or len(text) < 2:
                print(f"🗑️ [FILTRO] Texto descartado por ser basura/vacío.")
                return None
            
            return text

        except Exception as e:
            print(f"❌ Error: {e}")
            return None

    def say(self, text):
        if not text: return
        self.is_speaking = True
        print(f"🔊 [LUCY] {text[:50]}...")
        
        wav = os.path.abspath("response.wav")
        try:
            subprocess.run(["mimic3", "--voice", "es_ES/m-ailabs_low#karen_savage", text], stdout=open(wav, "wb"))
            if os.path.exists(wav): 
                subprocess.run(["paplay", wav])
        except: pass
        
        time.sleep(0.5)
        self.is_speaking = False
        print("🟢 [Mic] Reactivado.")
