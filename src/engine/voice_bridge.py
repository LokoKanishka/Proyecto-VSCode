import subprocess
import numpy as np
import os
import time
import torch
import wave

# --- CONFIGURACIÓN HÍBRIDA (LINUX NATIVE + AI) ---
SAMPLE_RATE = 16000
CHUNK_SIZE = 512  # Tamaño de bloque para Silero (512 muestras)
# En bytes: 512 muestras * 2 bytes (16-bit) = 1024 bytes
CHUNK_BYTES = CHUNK_SIZE * 2 

# PARÁMETROS DE FLUIDEZ (Estilo Géminis)
SPEECH_THRESHOLD = 0.5
MIN_SPEECH_DURATION_MS = 250
MAX_PAUSE_MS = 800          

class LucyVoiceBridge:
    def __init__(self):
        self.asr_model = None
        self.vad_model = None
        
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
            
            print("✅ [Engine] SISTEMA HÍBRIDO LISTO.")
        except Exception as e:
            print(f"❌ [Engine] Error Carga: {e}")

    def stop_listening(self):
        pass

    def listen_continuous(self):
        if not self.asr_model or not self.vad_model: return None
        
        # Resetear memoria neuronal
        try: self.vad_model.reset_states()
        except: pass

        print(f"\n🟢 [VAD] ESCUCHANDO... (Vía arecord nativo)")
        
        full_audio = []
        is_speaking = False
        silence_start_time = None
        speech_start_time = None
        
        min_speech_s = MIN_SPEECH_DURATION_MS / 1000.0
        max_pause_s = MAX_PAUSE_MS / 1000.0
        
        # --- LA MAGIA: USAR ARECORD NATIVO ---
        # Lanzamos el proceso de Linux en segundo plano y leemos su salida
        cmd = [
            "arecord", 
            "-D", "default", 
            "-f", "S16_LE", 
            "-r", str(SAMPLE_RATE), 
            "-c", "1", 
            "-t", "raw", 
            "-q" # Quiet mode (sin texto en pantalla)
        ]
        
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        
        try:
            while True:
                # Leemos exactamente 1024 bytes (512 samples) del tubo
                raw_bytes = process.stdout.read(CHUNK_BYTES)
                
                if not raw_bytes or len(raw_bytes) != CHUNK_BYTES:
                    continue

                # Convertir bytes a Numpy Float32 (Normalizado -1.0 a 1.0)
                # Int16 va de -32768 a 32767
                audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
                audio_float32 = audio_int16.astype(np.float32) / 32768.0
                
                # Convertir a Tensor para la IA
                audio_tensor = torch.from_numpy(audio_float32)

                # --- ANÁLISIS VAD ---
                try:
                    speech_prob = self.vad_model(audio_tensor, SAMPLE_RATE).item()
                except:
                    self.vad_model.reset_states()
                    speech_prob = 0.0

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
                        if silence_start_time is None:
                            silence_start_time = current_time
                        
                        full_audio.append(audio_float32) 
                        
                        silence_duration = current_time - silence_start_time
                        if silence_duration > max_pause_s:
                            total_speech_duration = current_time - speech_start_time - silence_duration
                            
                            if total_speech_duration < min_speech_s:
                                is_speaking = False
                                full_audio = []
                                continue
                            
                            print(f"\n✅ Fin de frase ({total_speech_duration:.1f}s). Transcribiendo...")
                            break
                            
        finally:
            # IMPORTANTE: Matar el proceso de arecord al terminar para no dejar zombies
            process.terminate()
            process.wait()

        if not full_audio: return None

        # --- TRANSCRIPCIÓN ---
        audio_data = np.concatenate(full_audio)
        
        try:
            segments, info = self.asr_model.transcribe(
                audio_data, beam_size=5, language="es", condition_on_previous_text=False,
                initial_prompt="Diálogo fluido."
            )
            text = " ".join([segment.text for segment in segments]).strip()
            
            ignored = ["thank you", "subtitles", "you", "copyright"]
            if not text or text.lower() in ignored:
                # print("   🗑️ (Silencio/Ruido ignorado)")
                return None
            
            return text

        except Exception as e:
            print(f"❌ Error Whisper: {e}")
            return None

    def say(self, text):
        if not text: return
        wav = os.path.abspath("response.wav")
        try:
            subprocess.run(["mimic3", "--voice", "es_ES/m-ailabs_low#karen_savage", text], stdout=open(wav, "wb"))
            if os.path.exists(wav): 
                subprocess.run(["paplay", wav])
        except: pass
        time.sleep(0.3) 
