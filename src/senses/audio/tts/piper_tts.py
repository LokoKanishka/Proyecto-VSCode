from pipecat.services.tts_service import TTSService
from pipecat.frames.frames import TTSStartedFrame, TTSStoppedFrame, TTSAudioRawFrame
import sounddevice as sd
import piper
import wave
import io
import numpy as np
from loguru import logger
import struct

class PiperTTSService(TTSService):
    """
    Local TTS using Piper (ONNX).
    """
    def __init__(self, model_path: str, device="cuda"):
        super().__init__()
        self.model_path = model_path
        # Piper python wrapper:
        # We use the piper package which provides Piper class
        self.voice = piper.PiperVoice.load(model_path)
        logger.info(f"🗣️ Piper TTS loaded from {model_path} (Device: {device})")
        # Ensure we are ready
        
    async def run_tts(self, text: str):
        logger.debug(f"🗣️ Synthesizing: {text}")
        yield TTSStartedFrame()
        
        # Piper generator
        # stream=True yields audio chunks (AudioChunk objects)
        stream = self.voice.synthesize(text)
        
        for chunk in stream:
            # chunk is AudioChunk with audio_int16_bytes
            audio = chunk.audio_int16_bytes
            
            # We need to verify sample rate from config
            sample_rate = self.voice.config.sample_rate
            yield TTSAudioRawFrame(audio=audio, sample_rate=sample_rate, num_channels=1)
            
        yield TTSStoppedFrame()

    async def say(self, text: str):
        """
        Direct audio output (bypass Pipecat transport for quick verification).
        """
        logger.info(f"🔊 Playing audio directly: {text}")
        stream = self.voice.synthesize_stream_raw(text)
        sample_rate = self.voice.config.sample_rate
        
        # Collect all audio to play (simpler than streaming to sd.OutputStream for check)
        # But for streaming we should use an OutputStream.
        
        audio_buffer = b""
        for chunk in stream:
            audio_buffer += chunk
            
        # Convert raw bytes to numpy for sounddevice
        audio_np = np.frombuffer(audio_buffer, dtype=np.int16)
        sd.play(audio_np, sample_rate)
        sd.wait()
