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
        
        # Detección de Mimic3 (preferimos venv o scripts locales)
        mimic_candidates = [
            os.path.join(os.path.dirname(sys.executable), "mimic3"),
            os.path.abspath(".venv/bin/mimic3"),
            os.path.abspath("scripts/bin/mimic3"),
            "/home/xdie/Proyecto-VSCode/.venv/bin/mimic3",
            "mimic3",
        ]
        self.mimic_path = next((p for p in mimic_candidates if os.path.exists(p) or subprocess.run(["which", p], capture_output=True).returncode == 0), "mimic3")
        
        print("⬇️ [Engine] Cargando Sistemas...")
        try:
            from faster_whisper import WhisperModel
            self.asr_model = WhisperModel("medium", device="cuda", compute_type="float16")
            
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
                audio_data,
                beam_size=5,
                language="es",
                condition_on_previous_text=False,
                initial_prompt="Lucy, Basilisco de Roko, Bitcoin, IA, Linux, Ubuntu, Python."
            )
            text = " ".join([segment.text for segment in segments]).strip()
            ignored = ["thank you", "subtitles", "you", "copyright"]
            if not text or text.lower() in ignored: return None
            return text
        except: return None

    def transcribe_file(self, wav_path):
        """
        Transcribe audio from WAV file (for web integration)
        
        Args:
            wav_path: Path to WAV file (16kHz mono recommended)
        
        Returns:
            str: Transcribed text or None
        """
        if not self.asr_model:
            return None
        
        if not os.path.exists(wav_path):
            return None
        
        try:
            # Read WAV file
            with wave.open(wav_path, 'rb') as wf:
                # Verify format
                if wf.getnchannels() != 1:
                    print(f"⚠️ Warning: Expected mono audio, got {wf.getnchannels()} channels")
                if wf.getframerate() != SAMPLE_RATE:
                    print(f"⚠️ Warning: Expected {SAMPLE_RATE}Hz, got {wf.getframerate()}Hz")
                
                # Read all frames
                frames = wf.readframes(wf.getnframes())
            
            # Convert to numpy array
            audio_int16 = np.frombuffer(frames, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            
            # Transcribe
            segments, info = self.asr_model.transcribe(
                audio_float32,
                beam_size=5,
                language="es",
                condition_on_previous_text=False,
                initial_prompt="Lucy, Basilisco de Roko, Bitcoin, IA, Linux, Ubuntu, Python."
            )
            
            # Extract text
            text = " ".join([segment.text for segment in segments]).strip()
            
            # Filter garbage
            ignored = ["thank you", "subtitles", "you", "copyright", "gracias por ver", "suscríbete"]
            if not text or text.lower() in ignored or len(text) < 3:
                return None
            
            print(f"✅ Transcribed: {text}")
            return text
            
        except Exception as e:
            print(f"❌ Transcription error: {e}")
            return None

    def say(self, text):
        if not text: return
        wav = os.path.abspath("response.wav")
        
        # 1. GENERAR AUDIO (Rápido)
        # print(f"🔊 Generando...")
        try:
            with open(wav, "wb") as wav_file:
                subprocess.run(
                    [self.mimic_path, "--voice", "es_ES/m-ailabs_low#karen_savage", text],
                    stdout=wav_file,
                    stderr=subprocess.DEVNULL
                )
        except:
            return

        if not os.path.exists(wav): return

        # 2. REPRODUCIR CON CAPACIDAD DE INTERRUPCIÓN
        print("▶️ Hablando... (Puedes interrumpirme)")
        
        # Lanzamos el reproductor en SEGUNDO PLANO (Non-blocking)
        player_process = subprocess.Popen(
            ["aplay", "-q", wav],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )
        
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
            if player_process.poll() is None:
                player_process.terminate()
                try:
                    player_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    player_process.kill()
            else:
                player_process.wait()
            monitor_process.terminate()
            monitor_process.wait()
        
        if interrupted:
            # Pequeña pausa para que el usuario termine de decir su palabra de interrupción
            # y el bucle principal lo capture limpio.
            time.sleep(0.1)
