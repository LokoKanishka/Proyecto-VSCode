import numpy as np
import threading
import time

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

class AudioProcessor:
    def __init__(self, channels=1, rate=16000, chunk_size=1024):
        self.channels = channels
        self.rate = rate
        self.chunk_size = chunk_size
        self.audio = None
        self.stream = None
        self.is_running = False
        
        # Internal buffers
        self.fft_data = np.zeros(self.chunk_size // 2)
        self.recording_buffer = [] # Accumulates raw chunks for STT
        self.max_buffer_samples = self.rate * 12 # 12 seconds max
        
        self.lock = threading.Lock()
        
        if PYAUDIO_AVAILABLE:
            try:
                self.audio = pyaudio.PyAudio()
                print(f"[AudioProcessor] Core Engine Initialized at {self.rate}Hz")
            except Exception as e:
                print(f"[AudioProcessor] Hardware Mic Error: {e}. Falling back to Synthetic.")
                self.audio = None
        else:
            print("[AudioProcessor] PyAudio unavailable. Synthetic active.")

    def start(self):
        if self.is_running: return
        self.is_running = True
        
        if self.audio:
            try:
                self.stream = self.audio.open(
                    format=pyaudio.paInt16,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk_size,
                    stream_callback=self._audio_callback
                )
                self.stream.start_stream()
            except Exception as e:
                print(f"[AudioProcessor] Failed to start hardware stream: {e}")
                self.audio = None
                threading.Thread(target=self._mock_loop, daemon=True).start()
        else:
            threading.Thread(target=self._mock_loop, daemon=True).start()

    def _audio_callback(self, in_data, frame_count, time_info, status):
        # Convert bytes to floats for analysis
        raw_int = np.frombuffer(in_data, dtype=np.int16)
        
        # APLICAR CALIBRACIÓN x4 (Propuesta por el usuario)
        # Esto aumenta la sensibilidad de Whisper
        norm_float = (raw_int.astype(np.float32) / 32768.0) * 4.0
        
        with self.lock:
            # 1. Update FFT for visualizer
            fft_complex = np.fft.fft(norm_float)
            fft_mag = np.abs(fft_complex[:self.chunk_size // 2])
            self.fft_data = np.clip(fft_mag / 15.0, 0, 1)
            
            # 2. Append to recording buffer for STT
            # Recortamos para evitar clipping extremo en memoria
            self.recording_buffer.append(np.clip(norm_float, -1.0, 1.0))
            
            # Buffer management
            samples_acc = len(self.recording_buffer) * self.chunk_size
            if samples_acc > self.max_buffer_samples:
                self.recording_buffer.pop(0)

        return (None, pyaudio.paContinue)

    def _mock_loop(self):
        """Generates pulsing energy for the pillars if no mic is found."""
        t = 0
        while self.is_running:
            with self.lock:
                mock_fft = np.zeros(self.chunk_size // 2)
                for i in range(len(mock_fft)):
                    # Pulsing pillars effect
                    val = 0.15 * np.abs(np.sin(t * 0.1 + i * 0.2)) + 0.05 * np.random.rand()
                    mock_fft[i] = val
                self.fft_data = mock_fft
                # Mock silence for recording
                self.recording_buffer.append(np.zeros(self.chunk_size, dtype=np.float32))
                if len(self.recording_buffer) * self.chunk_size > self.max_buffer_samples:
                    self.recording_buffer.pop(0)
            t += 1
            time.sleep(1/50)

    def get_fft_data(self):
        with self.lock:
            return self.fft_data.copy()

    def get_rms_level(self):
        """Returns current volume for VAD decisions."""
        fft = self.get_fft_data()
        if len(fft) > 0:
            return np.mean(fft[:10]) # Use low frequencies for voice level
        return 0

    def consume_buffer(self):
        """Returns accumulated audio and clears buffer."""
        with self.lock:
            if not self.recording_buffer:
                return np.array([], dtype=np.float32)
            data = np.concatenate(self.recording_buffer)
            self.recording_buffer = []
            return data

    def stop(self):
        self.is_running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()
