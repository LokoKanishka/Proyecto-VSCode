from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, InputAudioRawFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
from lucy_voice.config import LucyConfig
import webrtcvad
import logging
import numpy as np

class VADNode(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.config = config
        self.log = logging.getLogger("VADNode")
        self.vad = webrtcvad.Vad(3) # Mode 3: Aggressive
        
        self.sample_rate = config.sample_rate
        self.frame_duration_ms = 30 # webrtcvad supports 10, 20, 30
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        
        self.buffer = b""
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        
        # Parameters
        self.min_speech_frames = 5 # ~150ms
        self.min_silence_frames = 20 # ~600ms (Wait for 0.6s silence to stop)
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InputAudioRawFrame):
            # Accumulate buffer
            self.buffer += frame.audio
            
            # Process chunks of 30ms
            chunk_bytes = self.frame_size * 2 # 16-bit
            
            while len(self.buffer) >= chunk_bytes:
                chunk = self.buffer[:chunk_bytes]
                self.buffer = self.buffer[chunk_bytes:]
                
                is_speech = self.vad.is_speech(chunk, self.sample_rate)
                
                if is_speech:
                    self.speech_frames += 1
                    self.silence_frames = 0
                    if self.speech_frames >= self.min_speech_frames and not self.is_speaking:
                        self.is_speaking = True
                        self.log.info("VAD: User started speaking")
                        await self.push_frame(UserStartedSpeakingFrame(), direction)
                else:
                    self.silence_frames += 1
                    self.speech_frames = 0
                    if self.silence_frames >= self.min_silence_frames and self.is_speaking:
                        self.is_speaking = False
                        self.log.info("VAD: User stopped speaking")
                        await self.push_frame(UserStoppedSpeakingFrame(), direction)
            
            # Always pass audio through?
            # Or only when speaking?
            # Usually VAD passes all audio so ASR can have context, 
            # but marks start/stop.
            # ASR node will buffer and use the marks.
            await self.push_frame(frame, direction)
            
        else:
            await self.push_frame(frame, direction)
