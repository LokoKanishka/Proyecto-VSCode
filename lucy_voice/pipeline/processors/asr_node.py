from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, InputAudioRawFrame, TextFrame
from lucy_voice.asr.fast_whisper_wrapper import WhisperASR
from lucy_voice.config import LucyConfig
import numpy as np
import logging

class WhisperASRProcessor(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.asr = WhisperASR(config)
        self.log = logging.getLogger("WhisperASRProcessor")
        self.audio_buffer = []

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InputAudioRawFrame):
            # Accumulate audio
            # frame.audio is bytes
            # Convert to numpy for Whisper?
            # WhisperASR expects numpy array.
            # We assume float32 input from AudioNode
            audio_np = np.frombuffer(frame.audio, dtype=np.float32)
            self.audio_buffer.append(audio_np)
            
            # TODO: VAD logic
            
            await self.push_frame(frame, direction)
        
        elif isinstance(frame, TextFrame):
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)
