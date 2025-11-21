import logging
import subprocess
import io
import soundfile as sf
import numpy as np
from typing import Optional, Tuple
from lucy_voice.config import LucyConfig

class Mimic3TTS:
    def __init__(self, config: LucyConfig):
        self.config = config
        self.log = logging.getLogger("Mimic3TTS")

    def synthesize(self, text: str) -> Tuple[Optional[np.ndarray], int]:
        """
        Sintetiza texto a audio usando Mimic3.
        Returns: (audio_data, sample_rate)
        """
        self.log.info("Sintetizando audio con Mimic3 (voz=%s)...", self.config.tts_voice)

        try:
            proc = subprocess.run(
                ["mimic3", "--voice", self.config.tts_voice],
                input=text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.log.error("Error mimic3: %s", e)
            return None, 0

        # Leer WAV desde memoria
        try:
            with io.BytesIO(proc.stdout) as wav_io:
                data, sr = sf.read(wav_io, dtype="float32")
                return data, sr
        except Exception as e:
            self.log.error("Error leyendo output de mimic3: %s", e)
            return None, 0
