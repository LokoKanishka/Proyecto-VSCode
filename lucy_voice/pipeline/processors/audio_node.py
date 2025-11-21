from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, InputAudioRawFrame, OutputAudioRawFrame
from lucy_voice.pipeline.audio import AudioHandler
from lucy_voice.config import LucyConfig
import sounddevice as sd
import logging
import asyncio
import numpy as np

class AudioInputNode(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.config = config
        self.log = logging.getLogger("AudioInputNode")
        self.stream = None
        self.running = False

    async def start(self):
        self.running = True
        self.stream = sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            blocksize=int(self.config.sample_rate * 0.02), # 20ms chunks
        )
        self.stream.start()
        self.log.info("Audio input started")

    async def stop(self):
        self.running = False
        if self.stream:
            self.stream.stop()
            self.stream.close()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

    async def run_loop(self):
        """
        Manual loop to read audio and push frames.
        """
        self.log.info("Starting audio loop")
        with sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            blocksize=int(self.config.sample_rate * 0.1) # 100ms
        ) as stream:
            while self.running:
                data, overflow = stream.read(stream.blocksize)
                if overflow:
                    self.log.warning("Audio overflow")
                
                # data is numpy array (frames, channels)
                # InputAudioRawFrame expects bytes
                audio_bytes = data.tobytes()
                frame = InputAudioRawFrame(
                    audio=audio_bytes, 
                    sample_rate=self.config.sample_rate, 
                    num_channels=self.config.channels
                )
                await self.push_frame(frame, FrameDirection.DOWNSTREAM)
                await asyncio.sleep(0.01)

class AudioOutputNode(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.config = config
        self.log = logging.getLogger("AudioOutputNode")
        self.audio_handler = AudioHandler(config) # Reuse handler for playback

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, OutputAudioRawFrame):
            # Play audio
            # frame.audio is bytes.
            data = np.frombuffer(frame.audio, dtype=self.config.dtype)
            
            self.log.info(f"Playing audio frame ({len(data)} samples)")
            sd.play(data, self.config.sample_rate)
            sd.wait()
            
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)
