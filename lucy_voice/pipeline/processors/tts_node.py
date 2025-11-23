from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, TextFrame, OutputAudioRawFrame
from lucy_voice.tts.mimic_tts import Mimic3TTS
from lucy_voice.config import LucyConfig
import numpy as np
import logging

class MimicTTSProcessor(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.config = config
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
                # Resample if necessary (e.g. 22050 -> 16000)
                if sr != self.config.sample_rate:
                    self.log.info(f"Resampling TTS audio from {sr} to {self.config.sample_rate}")
                    duration = len(audio_data) / sr
                    new_num_samples = int(duration * self.config.sample_rate)
                    
                    old_indices = np.arange(len(audio_data))
                    new_indices = np.linspace(0, len(audio_data) - 1, new_num_samples)
                    
                    audio_data = np.interp(new_indices, old_indices, audio_data).astype(np.float32)
                    sr = self.config.sample_rate

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
