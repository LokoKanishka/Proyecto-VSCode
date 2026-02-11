import ray
import asyncio
from loguru import logger
from typing import AsyncGenerator

from pipecat.frames.frames import (
    EndFrame, 
    TextFrame, 
    Frame, 
    TTSStartedFrame, 
    TTSStoppedFrame, 
    TTSAudioRawFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.aggregators.llm_response import LLMUserResponseAggregator
from pipecat.services.whisper import WhisperSTTService
from pipecat.services.tts_service import TTSService
from pipecat.transports.services.daily import DailyParams, DailyTransport
from pipecat.audio.vad.silero import SileroVADAnalyzer
import sounddevice as sd
import numpy as np

class MockTTSService(TTSService):
    """
    Simple Mock TTS that yields silent frames.
    """
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    async def run_tts(self, text: str) -> AsyncGenerator[Frame, None]:
        logger.debug(f"Mock TTS saying: {text}")
        yield TTSStartedFrame()
        # Simulated audio output (silence)
        # 16000Hz * 0.1s * 2 bytes = 3200 bytes
        yield TTSAudioRawFrame(audio=b'\x00' * 3200, sample_rate=16000, num_channels=1)
        yield TTSStoppedFrame()

@ray.remote
class VoiceActor:
    """
    Ray Actor managing the Voice Pipeline (Pipecat).
    Handles Mic -> VAD -> STT -> Manager -> TTS.
    """
    def __init__(self):
        logger.info("🎤 VoiceActor initializing...")
        self.runner = None
        self.task = None
        self.transport = None
        self.stt = None
        self.vad = None
        self.interrupt_event = asyncio.Event()
        self.is_speaking = False
        
    async def start(self):
        """
        Starts the audio loop.
        """
        logger.info("🎤 Starting Voice Loop...")
        
        # Placeholder for valid VAD check
        try:
             self.vad = SileroVADAnalyzer()
             logger.info("✅ VAD Initialized")
        except Exception as e:
             logger.error(f"❌ VAD Init failed: {e}")

        # Placeholder for Whisper Local (using Mock/Empty for now to avoid model load)
        # self.stt = WhisperSTTService(model="base", device="cuda")
        
        # Piper TTS initialization (Real Audio)
        try:
             from lucy_voice.tts.piper_tts import PiperTTSService
             model_path = "models/piper/es_ES-sharvard-medium.onnx"
             self.tts = PiperTTSService(model_path=model_path, device="cuda")
             logger.info(f"✅ Piper TTS Initialized ({model_path})")
        except Exception as e:
             logger.error(f"❌ Piper Init failed: {e}. Falling back to Mock.")
             self.tts = MockTTSService()
        
        # Simulate VAD Monitoring loop in background
        asyncio.create_task(self._monitor_vad())
        
        logger.info("🎤 Voice Pipeline Ready (Standby Mode)")
        return "Voice Ready"

    async def _monitor_vad(self):
        """
        Simulate VAD loop. In real Pipecat this is handled by VAD node events.
        """
        while True:
            # Here we would await VAD events. 
            # For verification, we can manually trigger self.interrupt()
            await asyncio.sleep(0.1)

    async def interrupt(self):
        """
        External trigger to stop speech (Barge-in).
        """
        if self.is_speaking:
            logger.warning("🚫 Barge-in detected! Stopping TTS.")
            self.interrupt_event.set()

    async def speak(self, text: str):
        """
        TTS output with interruption support and audio playback.
        """
        logger.info(f"🔊 Speaking: {text}")
        self.is_speaking = True
        self.interrupt_event.clear()
        
        # Initialize Audio Stream (22050Hz is standard for Piper models)
        # We assume 1 channel, 16-bit (int16). 
        # Ideally, sample rate should come from the first frame or config.
        stream = None
        
        try:
            async for frame in self.tts.run_tts(text):
                if self.interrupt_event.is_set():
                    logger.info("🔇 TTS Interrupted.")
                    break
                
                if isinstance(frame, TTSAudioRawFrame):
                    if stream is None:
                        # Initialize stream with correct sample rate
                        stream = sd.OutputStream(
                            samplerate=frame.sample_rate, 
                            channels=frame.num_channels, 
                            dtype='int16'
                        )
                        stream.start()
                    
                    # Convert bytes to numpy and play
                    audio_np = np.frombuffer(frame.audio, dtype=np.int16)
                    stream.write(audio_np)
                
                # Yield control slightly to allow event loop to process interrupts
                await asyncio.sleep(0.01) 
        except Exception as e:
            logger.error(f"TTS Playback Error: {e}")
        finally:
            if stream:
                stream.stop()
                stream.close()
            self.is_speaking = False
            self.interrupt_event.clear()
        
        return True

    async def stop(self):
        if self.task:
            await self.task.cancel()
        logger.info("🎤 Voice Loop Stopped")

