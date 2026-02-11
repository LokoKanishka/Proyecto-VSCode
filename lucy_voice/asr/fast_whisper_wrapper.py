import logging
from typing import Tuple
import numpy as np
from faster_whisper import WhisperModel
from lucy_voice.config import LucyConfig

class WhisperASR:
    def __init__(self, config: LucyConfig):
        self.config = config
        self.log = logging.getLogger("WhisperASR")
        
        self.log.info(
            "Cargando modelo Whisper %r (device=%s, compute_type=%s)...",
            self.config.whisper_model_name,
            self.config.whisper_device,
            self.config.whisper_compute_type,
        )
        self.model = WhisperModel(
            self.config.whisper_model_name,
            device=self.config.whisper_device,
            compute_type=self.config.whisper_compute_type,
        )

    def transcribe(self, audio: np.ndarray) -> Tuple[str, str]:
        """
        Transcribe audio en memoria.
        Devuelve (texto, idioma_detectado).
        """
        audio_f32 = audio.astype("float32")

        # Lucy Voz: forzamos language="es" para mejorar estabilidad en entorno hispanohablante.
        language = self.config.whisper_language if self.config.whisper_force_language else None
        task = self.config.whisper_task or "transcribe"

        segments, info = self.model.transcribe(
            audio_f32,
            beam_size=1,
            vad_filter=False,
            language=language,
            task=task,
        )

        text_chunks = []
        for seg in segments:
            text_chunks.append(seg.text.strip())
        text = " ".join(t for t in text_chunks if t)

        lang = info.language or "unknown"
        self.log.info(
            "Texto reconocido: %r (lang=%s, p=%.2f)",
            text,
            lang,
            info.language_probability or 0.0,
        )
        return text, lang
