import asyncio
import logging
import threading
import numpy as np
import sounddevice as sd
import webrtcvad
from lucy_voice.config import LucyConfig

class AudioHandler:
    def __init__(self, config: LucyConfig):
        self.config = config
        self.log = logging.getLogger("AudioHandler")
        self.is_speaking = False
        self.interrupt_flag = threading.Event()

    def record_fixed(self, seconds: float) -> np.ndarray:
        frames = int(seconds * self.config.sample_rate)
        self.log.info(
            "Grabando audio fijo: %.1fs a %d Hz...",
            seconds,
            self.config.sample_rate,
        )
        audio = sd.rec(
            frames,
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
        )
        sd.wait()
        self.log.info(
            "Audio grabado: %.2fs",
            len(audio) / self.config.sample_rate,
        )
        return audio.reshape(-1)

    def record_until_silence(self, max_seconds: float = 10.0, silence_duration: float = 1.0) -> np.ndarray:
        vad = webrtcvad.Vad(self.config.vad_aggressiveness)
        frame_duration_ms = self.config.vad_frame_duration_ms
        frame_size = int(self.config.sample_rate * frame_duration_ms / 1000)
        
        self.log.info("Grabando con VAD (max %.1fs)...", max_seconds)
        
        frames = []
        silence_frames = 0
        silence_threshold = int(silence_duration * 1000 / frame_duration_ms)
        max_frames = int(max_seconds * 1000 / frame_duration_ms)
        
        with sd.InputStream(samplerate=self.config.sample_rate, channels=self.config.channels, dtype=self.config.dtype) as stream:
            for _ in range(max_frames):
                audio_chunk, _ = stream.read(frame_size)
                audio_f32 = audio_chunk[:, 0]
                frames.append(audio_f32)
                
                # Convertir a int16 para VAD
                audio_int16 = (audio_f32 * 32767).astype(np.int16).tobytes()
                
                try:
                    is_speech = vad.is_speech(audio_int16, self.config.sample_rate)
                except Exception:
                    is_speech = False
                
                if is_speech:
                    silence_frames = 0
                else:
                    silence_frames += 1
                    
                if silence_frames >= silence_threshold:
                    self.log.info("Silencio detectado, finalizando grabación.")
                    break
        
        if not frames:
            return np.array([], dtype=self.config.dtype)

        audio = np.concatenate(frames)
        self.log.info("Audio grabado: %.2fs", len(audio) / self.config.sample_rate)
        return audio

    def play_audio(self, data: np.ndarray, samplerate: int) -> bool:
        """
        Reproduce audio con capacidad de interrupción.
        Returns: True si fue interrumpido, False si terminó.
        """
        self.is_speaking = True
        self.interrupt_flag.clear()
        
        monitor_thread = self._start_interruption_monitor()
        
        stream = sd.OutputStream(samplerate=samplerate, channels=1, dtype='float32')
        stream.start()
        
        chunk_size = int(samplerate * 0.1)  # 100ms chunks
        interrupted = False
        
        try:
            for i in range(0, len(data), chunk_size):
                if self.interrupt_flag.is_set():
                    self.log.info("¡Interrumpido! Deteniendo audio...")
                    interrupted = True
                    break
                
                chunk = data[i:i+chunk_size]
                # Ensure chunk is float32
                chunk = chunk.astype(np.float32)
                stream.write(chunk)
        except Exception as e:
            self.log.error(f"Error durante reproducción: {e}")
        finally:
            stream.stop()
            stream.close()
            self.is_speaking = False
            # Wait for monitor to finish? It checks is_speaking loop
        
        return interrupted

    def _start_interruption_monitor(self) -> threading.Thread:
        def monitor():
            try:
                # self.log.debug("Iniciando monitor de interrupción...")
                energy_threshold = 0.01
                consecutive_speech_chunks = 0
                required_chunks = 2
                
                while self.is_speaking:
                    # Grabar chunk pequeño
                    # Note: sd.rec is blocking, but we are in a thread.
                    # However, we can't use sd.rec if we are also playing audio with sd?
                    # PortAudio supports full duplex usually.
                    
                    try:
                        audio = sd.rec(
                            int(self.config.sample_rate * 0.2),
                            samplerate=self.config.sample_rate,
                            channels=self.config.channels,
                            dtype=self.config.dtype,
                            blocking=True 
                        )
                    except Exception:
                        # If device is busy or fails
                        break

                    audio_f32 = audio.reshape(-1).astype("float32")
                    energy = np.sqrt(np.mean(audio_f32**2))
                    
                    if energy > energy_threshold:
                        consecutive_speech_chunks += 1
                        if consecutive_speech_chunks >= required_chunks:
                            self.log.info(f"¡INTERRUMPIENDO! (energía: {energy:.4f})")
                            self.interrupt_flag.set()
                            return
                    else:
                        consecutive_speech_chunks = 0
                            
            except Exception as e:
                self.log.error(f"Error en monitor de interrupción: {e}")
        
        thread = threading.Thread(target=monitor, daemon=True)
        thread.start()
        return thread


class AudioCaptureGate:
    """Synchronization primitive to pause/resume audio capture."""

    def __init__(self) -> None:
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._pause_count = 0
        self._lock = threading.Lock()

    def pause(self) -> None:
        with self._lock:
            self._pause_count += 1
            if self._pause_count == 1:
                self._pause_event.clear()

    def resume(self) -> None:
        with self._lock:
            if self._pause_count == 0:
                return
            self._pause_count -= 1
            if self._pause_count == 0:
                self._pause_event.set()

    def is_paused(self) -> bool:
        with self._lock:
            return self._pause_count > 0

    async def wait_for_resume(self) -> None:
        await self._pause_event.wait()
