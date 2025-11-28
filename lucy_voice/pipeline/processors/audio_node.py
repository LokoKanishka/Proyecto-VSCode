from pipecat.processors.frame_processor import FrameProcessor, FrameDirection
from pipecat.frames.frames import Frame, InputAudioRawFrame, OutputAudioRawFrame, StartFrame, EndFrame
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
        self.log.info("AudioInputNode initialized (v2)")
        self._audio_task = None
        self._running = False

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Log ANY frame received
        self.log.debug(f"AudioInputNode received frame: {type(frame)} from {direction}")
        
        # Let base class handle state and propagation first
        await super().process_frame(frame, direction)
        
        # We must push the StartFrame downstream so other nodes receive it!
        await self.push_frame(frame, direction)
        
        if isinstance(frame, StartFrame):
            self.log.info("Manual StartFrame detection triggered")
            await self.handle_start(frame)

    async def handle_start(self, frame: StartFrame):
        """Called when StartFrame is received - this is when we start audio capture"""
        self.log.info(f"AudioInputNode received StartFrame: {frame}")
        # await super().handle_start(frame) # FrameProcessor does not have handle_start
        
        self.log.info("Audio input started")
        self._running = True
        
        # Give StartFrame a moment to propagate to downstream nodes
        await asyncio.sleep(0.2)
        
        # Start the audio loop
        self._audio_task = asyncio.create_task(self._audio_loop())
        
        # StartFrame is already pushed by super().process_frame in process_frame
        # await self.push_frame(frame, FrameDirection.DOWNSTREAM)

    async def handle_end(self, frame: EndFrame):
        """Called when EndFrame is received - cleanup"""
        self._running = False
        if self._audio_task:
            self._audio_task.cancel()
            try:
                await self._audio_task
            except asyncio.CancelledError:
                pass
            self._audio_task = None
        
        await super().handle_end(frame)

    async def _audio_loop(self):
        """Internal loop to read audio and push frames"""
        self.log.info("Starting audio capture loop")
        
        with sd.InputStream(
            samplerate=self.config.sample_rate,
            channels=self.config.channels,
            dtype=self.config.dtype,
            blocksize=int(self.config.sample_rate * 0.1) # 100ms
        ) as stream:
            while self._running:
                try:
                    # Run blocking read in a separate thread
                    data, overflow = await asyncio.to_thread(stream.read, stream.blocksize)
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
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    self.log.error(f"Error in audio loop: {e}")
                    break



class AudioOutputNode(FrameProcessor):
    def __init__(self, config: LucyConfig, on_complete=None):
        super().__init__()
        self.config = config
        self.log = logging.getLogger("AudioOutputNode")
        self.audio_handler = AudioHandler(config) # Reuse handler for playback
        self.on_complete = on_complete

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
            
            # Use frame sample rate if available, else config
            sr = getattr(frame, 'sample_rate', self.config.sample_rate)
            
            sd.play(data, sr)
            sd.wait()
            
            if self.on_complete:
                if asyncio.iscoroutinefunction(self.on_complete):
                    await self.on_complete()
                else:
                    self.on_complete()
            
            await self.push_frame(frame, direction)
        else:
            await self.push_frame(frame, direction)
