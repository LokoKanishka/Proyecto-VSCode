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
        self.vad = webrtcvad.Vad(self.config.vad_aggressiveness)
        
        self.sample_rate = config.sample_rate
        self.frame_duration_ms = config.vad_frame_duration_ms or 30 # webrtcvad supports 10, 20, 30
        self.frame_size = int(self.sample_rate * self.frame_duration_ms / 1000)
        
        self.buffer = b""
        self.is_speaking = False
        self.silence_frames = 0
        self.speech_frames = 0
        self.utterance_frames = 0
        
        # Parameters (derived so they remain configurable in YAML)
        self.min_speech_frames = max(1, int(self.config.vad_min_speech_ms / self.frame_duration_ms)) # ~300ms
        self.min_silence_frames = max(1, int(self.config.vad_silence_duration_ms / self.frame_duration_ms)) # ~0.9s
        self.min_utterance_frames = max(
            self.min_speech_frames,
            int(self.config.vad_min_utterance_ms / self.frame_duration_ms),
        ) # ~1.7-1.8s of total window before allowing stop
        self.max_utterance_frames = max(
            self.min_utterance_frames,
            int((self.config.max_record_seconds * 1000) / self.frame_duration_ms),
        )
        
    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)
        
        if direction != FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if isinstance(frame, InputAudioRawFrame):
            # El audio viene como float32 [-1, 1] desde AudioInputNode
            audio_f32 = np.frombuffer(frame.audio, dtype=np.float32)

            # webrtcvad espera int16 a 16 kHz
            audio_i16 = np.clip(audio_f32 * 32767.0, -32768, 32767).astype(np.int16)
            audio_bytes = audio_i16.tobytes()

            # Acumulamos en el buffer pero ya en formato int16
            self.buffer += audio_bytes

            # Procesamos chunks de 30 ms (16-bit)
            chunk_bytes = self.frame_size * 2  # 16-bit

            while len(self.buffer) >= chunk_bytes:
                chunk = self.buffer[:chunk_bytes]
                self.buffer = self.buffer[chunk_bytes:]

                is_speech = self.vad.is_speech(chunk, self.sample_rate)

                if is_speech:
                    self.speech_frames += 1
                    self.silence_frames = 0
                    if self.is_speaking:
                        self.utterance_frames += 1
                    if self.speech_frames >= self.min_speech_frames and not self.is_speaking:
                        self.is_speaking = True
                        self.utterance_frames = self.speech_frames
                        self.log.info("VAD: User started speaking")
                        await self.push_frame(UserStartedSpeakingFrame(), direction)
                else:
                    self.silence_frames += 1
                    self.speech_frames = 0
                    if self.is_speaking:
                        self.utterance_frames += 1

                        if self.utterance_frames >= self.max_utterance_frames:
                            self.log.info("VAD: Max utterance reached, forcing stop.")
                            self.is_speaking = False
                            self.silence_frames = 0
                            self.speech_frames = 0
                            self.utterance_frames = 0
                            await self.push_frame(UserStoppedSpeakingFrame(), direction)
                            continue

                        if self.silence_frames >= self.min_silence_frames:
                            if self.utterance_frames < self.min_utterance_frames:
                                self.log.info(
                                    "VAD: Ignoring short utterance (%.2fs) and waiting...",
                                    (self.utterance_frames * self.frame_duration_ms) / 1000.0,
                                )
                                continue

                            self.is_speaking = False
                            self.log.info("VAD: User stopped speaking")
                            await self.push_frame(UserStoppedSpeakingFrame(), direction)
                            self.utterance_frames = 0
                            self.silence_frames = 0

            # Siempre pasamos el frame hacia abajo
            await self.push_frame(frame, direction)
            
        else:
            await self.push_frame(frame, direction)
