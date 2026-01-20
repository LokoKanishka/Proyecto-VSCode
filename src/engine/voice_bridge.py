import threading
import subprocess
import numpy as np
import sounddevice as sd
import os
import time
import wave
import queue

# --- CONFIGURACIÓN DE FLUJO CONTINUO ---
SAMPLE_RATE = 16000
DIGITAL_GAIN = 2.0      # Ganancia segura para evitar saturación
SILENCE_THRESHOLD = 0.3
SILENCE_TIMEOUT = 2.0   # Segundos de silencio para cortar
MAX_RECORD_TIME = 20    # Límite máximo

class LucyVoiceBridge:
    def __init__(self):
        self.asr_model = None
        self.should_record = False
        self.audio_queue = queue.Queue() # El "balde" donde cae el audio
        try:
            from faster_whisper import WhisperModel
            print("⬇️ [Engine] Cargando Whisper 'small'...")
            self.asr_model = WhisperModel("small", device="cpu", compute_type="int8")
            print("✅ [Engine] OÍDO LISTO.")
        except Exception as e:
            print(f"❌ [Engine] Error Carga: {e}")

    def stop_listening(self):
        self.should_record = False

    # Esta función se ejecuta sola en segundo plano por el driver
    def audio_callback(self, indata, frames, time, status):
        if status:
            print(status, flush=True)
        if self.should_record:
            self.audio_queue.put(indata.copy()) # Meter audio al balde

    def listen_once(self, callback_text):
        if not self.asr_model: return
        self.should_record = True
        print(f"🟢 [Mic] ESCUCHANDO... (Fluido y Continuo)")
        
        full_audio = []
        start_time = time.time()
        last_sound_time = time.time()
        
        # Vaciamos la cola vieja
        while not self.audio_queue.empty():
            self.audio_queue.get()

        # ABRIMOS EL GRIFO (InputStream)
        # blocksize=2000 son trocitos pequeños para baja latencia
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, callback=self.audio_callback, blocksize=4000):
            while self.should_record:
                # Sacamos audio del balde
                try:
                    chunk = self.audio_queue.get(timeout=1.0)
                except queue.Empty:
                    continue # Si no hay audio, esperamos
                
                # Procesamiento (Ahora esto ocurre MIENTRAS se sigue grabando el siguiente trozo)
                chunk = chunk.flatten() * DIGITAL_GAIN
                vol = np.linalg.norm(chunk) * 10
                
                if vol > SILENCE_THRESHOLD:
                    last_sound_time = time.time()
                    print(f"   🎤 Nivel: {vol:.1f}   ", end="\r")
                
                full_audio.append(chunk)
                
                # Detección de Silencio
                if time.time() - last_sound_time > SILENCE_TIMEOUT and len(full_audio) > 10:
                    print("\n✂️ Silencio detectado. Procesando...")
                    break
                
                if time.time() - start_time > MAX_RECORD_TIME:
                    print("\n⚠️ Tiempo límite.")
                    break

        self.should_record = False

        if not full_audio: return
        audio_data = np.concatenate(full_audio)
        
        # --- DEBUG: GUARDAR LO QUE ESCUCHÓ ---
        try:
            int16_audio = (audio_data / np.max(np.abs(audio_data)) * 32767).astype(np.int16)
            with wave.open("debug_last_record.wav", 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(SAMPLE_RATE)
                wf.writeframes(int16_audio.tobytes())
        except: pass
        # -------------------------------------

        # Normalizar
        max_val = np.max(np.abs(audio_data))
        if max_val > 0: audio_data = audio_data / max_val

        try:
            segments, info = self.asr_model.transcribe(
                audio_data, beam_size=5, language="es", condition_on_previous_text=False,
                initial_prompt="Hola. Háblame del Martín Fierro."
            )
            text = " ".join([segment.text for segment in segments]).strip()
            
            ignored = ["thank you", "subtitles"]
            if text.lower() in ignored or len(text) < 2:
                print(f"🗑️ Ignorado: {text}")
                return
            
            print(f"📝 [Transcripción] '{text}'")
            callback_text(text)

        except Exception as e:
            print(f"❌ Error Transcripción: {e}")

    def say(self, text):
        if not text: return
        threading.Thread(target=self._speak_thread, args=(text,)).start()

    def _speak_thread(self, text):
        wav = os.path.abspath("response.wav")
        try:
            subprocess.run(["mimic3", "--voice", "es_ES/m-ailabs_low#karen_savage", text], stdout=open(wav, "wb"))
            if os.path.exists(wav): subprocess.run(["paplay", wav])
        except: pass
