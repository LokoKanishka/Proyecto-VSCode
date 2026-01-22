import subprocess
import numpy as np
import os
import time
import torch
import wave
import sys

# --- CONFIGURACIÓN ---
SAMPLE_RATE = 16000
CHUNK_SIZE = 512 
CHUNK_BYTES = CHUNK_SIZE * 2 

# PARÁMETROS DE INTERRUPCIÓN
SPEECH_THRESHOLD = 0.5
MIN_SPEECH_DURATION_MS = 250
MAX_PAUSE_MS = 800
INTERRUPTION_SENSITIVITY = 0.6 # Un poco más alto para evitar auto-interrupciones por eco leve

class LucyVoiceBridge:
    def __init__(self):
        self.asr_model = None
        self.vad_model = None
        
        # Detección de Mimic3
        self.mimic_path = os.path.join(os.path.dirname(sys.executable), "mimic3")
        if not os.path.exists(self.mimic_path):
            self.mimic_path = "mimic3"
        
        print("⬇️ [Engine] Cargando Sistemas...")
        try:
            from faster_whisper import WhisperModel
            self.asr_model = WhisperModel("small", device="cpu", compute_type="int8")
            
            print("⬇️ [Engine] Cargando Silero VAD...")
            self.vad_model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                                   model='silero_vad',
                                                   force_reload=False,
                                                   onnx=False)
            self.get_speech_timestamps, _, _, _, _ = utils
            
            print("✅ [Engine] SISTEMA FULL-DUPLEX LISTO.")
        except Exception as e:
            print(f"❌ [Engine] Error Carga: {e}")

    def stop_listening(self):
        pass

    def _get_arecord_cmd(self):
        return [
            "arecord", "-D", "default", "-f", "S16_LE", 
            "-r", str(SAMPLE_RATE), "-c", "1", "-t", "raw", "-q"
        ]

    def listen_continuous(self):
        if not self.asr_model or not self.vad_model: return None
        
        try: self.vad_model.reset_states()
        except: pass

        print(f"\n🟢 [VAD] ESCUCHANDO... (Esperando tu orden)")
        
        full_audio = []
        is_speaking = False
        silence_start_time = None
        speech_start_time = None
        min_speech_s = MIN_SPEECH_DURATION_MS / 1000.0
        max_pause_s = MAX_PAUSE_MS / 1000.0
        
        process = subprocess.Popen(self._get_arecord_cmd(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        try:
            while True:
                raw_bytes = process.stdout.read(CHUNK_BYTES)
                if not raw_bytes or len(raw_bytes) != CHUNK_BYTES: continue

                audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_float32)

                try: speech_prob = self.vad_model(audio_tensor, SAMPLE_RATE).item()
                except: speech_prob = 0.0

                current_time = time.time()

                if speech_prob > SPEECH_THRESHOLD:
                    if not is_speaking:
                        is_speaking = True
                        speech_start_time = current_time
                        print("   🗣️ Voz detectada...", end="\r")
                    silence_start_time = None
                    full_audio.append(audio_float32)
                else:
                    if is_speaking:
                        if silence_start_time is None: silence_start_time = current_time
                        full_audio.append(audio_float32) 
                        if (current_time - silence_start_time) > max_pause_s:
                            total = current_time - speech_start_time - (current_time - silence_start_time)
                            if total < min_speech_s:
                                is_speaking = False
                                full_audio = []
                                continue
                            print(f"\n✅ Fin de frase ({total:.1f}s). Transcribiendo...")
                            break
        finally:
            process.terminate()
            process.wait()

        if not full_audio: return None
        audio_data = np.concatenate(full_audio)
        
        try:
            segments, info = self.asr_model.transcribe(
                audio_data, beam_size=5, language="es", condition_on_previous_text=False,
                initial_prompt="Diálogo fluido."
            )
            text = " ".join([segment.text for segment in segments]).strip()
            ignored = ["thank you", "subtitles", "you", "copyright"]
            if not text or text.lower() in ignored: return None
            return text
        except: return None

    def say(self, text):
        if not text: return
        wav = os.path.abspath("response.wav")
        
        # 1. GENERAR AUDIO (Rápido)
        # print(f"🔊 Generando...")
        try:
            subprocess.run([self.mimic_path, "--voice", "es_ES/m-ailabs_low#karen_savage", text], 
                           stdout=open(wav, "wb"), stderr=subprocess.PIPE)
        except: return

        if not os.path.exists(wav): return

        # 2. REPRODUCIR CON CAPACIDAD DE INTERRUPCIÓN
        print("▶️ Hablando... (Puedes interrumpirme)")
        
        # Lanzamos el reproductor en SEGUNDO PLANO (Non-blocking)
        player_process = subprocess.Popen(["aplay", "-q", wav])
        
        # Lanzamos el GRABADOR para detectar interrupciones
        monitor_process = subprocess.Popen(self._get_arecord_cmd(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        interrupted = False
        
        try:
            # Mientras Lucy habla...
            while player_process.poll() is None:
                # Leemos el micrófono
                raw_bytes = monitor_process.stdout.read(CHUNK_BYTES)
                if not raw_bytes or len(raw_bytes) != CHUNK_BYTES: continue
                
                # Chequeamos si hay voz humana
                audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                audio_tensor = torch.from_numpy(audio_float32)
                
                try: prob = self.vad_model(audio_tensor, SAMPLE_RATE).item()
                except: prob = 0.0
                
                # SI DETECTAMOS VOZ -> INTERRUPCIÓN
                if prob > INTERRUPTION_SENSITIVITY:
                    print("\n✋ INTERRUPCIÓN DETECTADA. Callando...")
                    player_process.terminate() # Matar audio
                    interrupted = True
                    break
        finally:
            # Limpieza
            if player_process.poll() is None: player_process.terminate()
            monitor_process.terminate()
            monitor_process.wait()
        
        if interrupted:
            # Pequeña pausa para que el usuario termine de decir su palabra de interrupción
            # y el bucle principal lo capture limpio.
            time.sleep(0.1)
