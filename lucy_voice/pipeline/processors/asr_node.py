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
            self.audio_buffer = []
            await self.push_frame(frame, direction)
            
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self.log.info("ASR: Stop recording & Transcribe")
            self.is_recording = False
            
            if self.audio_buffer:
                # Concatenar todo el audio grabado (float32, 16 kHz)
                audio_np = np.concatenate(self.audio_buffer)
                
                # El wrapper puede devolver:
                #  - sólo texto (str)
                #  - o (texto, idioma)
                result = self.asr.transcribe(audio_np)
                
                lang = None
                if isinstance(result, tuple):
                    text, lang = result
                else:
                    text = result
                
                if isinstance(text, str) and text.strip():
                    clean = text.strip()
                    self.log.info("ASR final text: %r (lang=%r)", clean, lang)
                    # Enviamos texto al LLM
                    await self.push_frame(TextFrame(clean), direction)
                else:
                    self.log.info("ASR: Empty transcription (text=%r, lang=%r)", text, lang)
                
                # Limpiamos buffer después de transcribir
                self.audio_buffer = []
            else:
                self.log.info("ASR: No audio to transcribe")
            
            # También dejamos pasar el frame de StopSpeaking
            await self.push_frame(frame, direction)

        elif isinstance(frame, InputAudioRawFrame):
            # Bufferear solo mientras se está grabando
            if self.is_recording:
                audio_np = np.frombuffer(frame.audio, dtype=np.float32)
                if audio_np.size > 0:
                    self.audio_buffer.append(audio_np)
            
            # Siempre dejamos pasar el audio hacia abajo en la pipeline
            await self.push_frame(frame, direction)
            
        else:
            await self.push_frame(frame, direction)

