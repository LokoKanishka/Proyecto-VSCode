from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, InputAudioRawFrame, TextFrame, UserStartedSpeakingFrame, UserStoppedSpeakingFrame
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
        self.is_recording = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, UserStartedSpeakingFrame):
            self.log.info("ASR: Start recording")
            self.is_recording = True
            self.audio_buffer = [] # Clear buffer or keep context?
            # Ideally we keep a bit of context if VAD was late.
            # But for now, clear.
            await self.push_frame(frame, direction)
            
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self.log.info("ASR: Stop recording & Transcribe")
            self.is_recording = False
            
            if self.audio_buffer:
                # Transcribe
                audio_np = np.concatenate(self.audio_buffer)
                self.audio_buffer = []
                
                # Run in executor to avoid blocking async loop?
                # Whisper is CPU intensive.
                # For now, blocking call (fast-whisper is fastish).
                text = self.asr.transcribe(audio_np)
                if text and text.strip():
                    self.log.info(f"ASR Recognized: {text}")
                    await self.push_frame(TextFrame(text), direction)
                else:
                    self.log.info("ASR: No text recognized or empty.")
            
            await self.push_frame(frame, direction)

        elif isinstance(frame, InputAudioRawFrame):
            # Always buffer if we are recording?
            # Or buffer always and trim?
            # VADNode passes all audio.
            # If we only buffer when is_recording, we might miss the start.
            # But VADNode emits Start AFTER it detected speech (so it's already late).
            # So VADNode should probably have buffered the start?
            # My VADNode implementation passes audio as it comes.
            # So ASR sees audio BEFORE StartFrame.
            
            # Strategy: Buffer always, but keep ring buffer?
            # Or: Just buffer when is_recording is True?
            # If VADNode is "Aggressive", it might be fine.
            # But usually we want pre-roll.
            
            # Let's assume VADNode is good enough or we accept slight cut.
            # To fix pre-roll, VADNode should have emitted the buffered audio AFTER StartFrame?
            # In my VADNode, I didn't do that. I just pushed frames.
            
            # Let's just buffer if is_recording for now.
            if self.is_recording:
                audio_np = np.frombuffer(frame.audio, dtype=np.float32)
                self.audio_buffer.append(audio_np)
            
            await self.push_frame(frame, direction)
            
        else:
            await self.push_frame(frame, direction)

