from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TextFrame, OutputAudioRawFrame
from lucy_voice.tts.mimic_tts import Mimic3TTS
from lucy_voice.config import LucyConfig
import logging

class MimicTTSProcessor(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.tts = Mimic3TTS(config)
        self.log = logging.getLogger("MimicTTSProcessor")

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, TextFrame):
            text = frame.text
            self.log.info(f"Synthesizing: {text}")
            audio_data, sr = self.tts.synthesize(text)
            
            if audio_data is not None:
                # audio_data is numpy array (float32 usually)
                audio_bytes = audio_data.tobytes()
                # OutputAudioRawFrame(audio, sample_rate, num_channels)
                # Mimic3 usually mono
                out_frame = OutputAudioRawFrame(
                    audio=audio_bytes,
                    sample_rate=sr,
                    num_channels=1
                )
                await self.push_frame(out_frame, direction)
            else:
                self.log.error("TTS failed")
        else:
            await self.push_frame(frame, direction)
