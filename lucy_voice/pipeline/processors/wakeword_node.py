from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, InputAudioRawFrame
from lucy_voice.config import LucyConfig
from openwakeword.model import Model
import numpy as np
import logging
import time

class WakeWordNode(FrameProcessor):
    def __init__(self, config: LucyConfig):
        super().__init__()
        self.config = config
        self.log = logging.getLogger("WakeWordNode")
        
        # Load model
        model_paths = config.wakeword_model_paths
        if not model_paths:
            # Fallback or default
            self.model = Model()
        else:
            self.model = Model(wakeword_model_paths=model_paths)
            
        self.is_woken = False
        self.cooldown = config.wakeword_cooldown
        self.last_wake_time = 0
        self.buffer = [] # Buffer for wake word detection (chunking)
        self.chunk_size = 1280 # OpenWakeWord expects chunks of 1280 samples (80ms at 16k)

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InputAudioRawFrame):
            # If already woken, pass through
            if self.is_woken:
                await self.push_frame(frame, direction)
                return

            # Not woken, run detection
            audio_data = np.frombuffer(frame.audio, dtype=np.int16)
            
            # OpenWakeWord expects 1280 chunks.
            # We might get different sizes. We need to buffer.
            self.buffer.extend(audio_data)
            
            while len(self.buffer) >= self.chunk_size:
                chunk = np.array(self.buffer[:self.chunk_size], dtype=np.int16)
                self.buffer = self.buffer[self.chunk_size:]
                
                # Predict
                prediction = self.model.predict(chunk)
                
                # Check prediction
                # We check all models
                for name, score in prediction.items():
                    if score >= self.config.wakeword_threshold:
                        now = time.time()
                        if now - self.last_wake_time > self.cooldown:
                            self.log.info(f"Wake Word Detected: {name} ({score:.3f})")
                            self.is_woken = True
                            self.last_wake_time = now
                            
                            # Emit a signal? Or just start passing frames?
                            # We should probably pass the *current* chunk and subsequent ones?
                            # Or maybe the user started speaking immediately.
                            # Let's pass this chunk and future ones.
                            
                            # Also, we might want to emit a "WakeDetected" frame if Pipecat has one,
                            # or just let VAD pick up the speech.
                            pass
            
            # If we just woke up, we might have leftover buffer to send?
            # For simplicity, we start sending from next frame.
            
            if self.is_woken:
                # We just woke up.
                # Pass the frame (or what's left of it)?
                # The frame was consumed by buffer.
                # We can reconstruct frame from buffer? No, buffer is int16.
                # InputAudioRawFrame is bytes.
                # It's complicated to reconstruct exact frame boundaries.
                # But since we are in "Not Woken" state, we were dropping frames anyway.
                # So it's fine to start passing from NEXT frame.
                pass
        
        else:
            # Pass other frames (StartFrame, TextFrame, etc)
            await self.push_frame(frame, direction)

    def reset(self):
        self.log.info("Resetting WakeWordNode (Sleeping)")
        self.is_woken = False
        self.buffer = []
        self.model.reset()

