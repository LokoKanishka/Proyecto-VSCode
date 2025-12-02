#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

cat > lucy_voice/pipeline_lucy_voice.py << 'PYEOF'
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = "float32"


@dataclass
class LucyPipelineConfig:
    whisper_model_name: str = "Systran/faster-whisper-small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    ollama_model: str = "gpt-oss:20b"
    ollama_host: str = "http://localhost:11434"
    tts_voice: str = "es_ES/m-ailabs_low"
    # segundos de audio que se graban después de la activación
    record_seconds: float = 4.0


class LucyVoicePipeline:
    def __init__(self, config: Optional[LucyPipelineConfig] = None) -> None:
        self.log = logging.getLogger("LucyVoicePipeline")
        self.config = config or LucyPipelineConfig()

        self.log.info(
            "Cargando modelo Whisper %r (device=%s, compute_type=%s)...",
            self.config.whisper_model_name,
            self.config.whisper_device,
            self.config.whisper_compute_type,
        )
        self.whisper_model = WhisperModel(
            self.config.whisper_model_name,
            device=self.config.whisper_device,
            compute_type=self.config.whisper_compute_type,
        )

    # ----------------- Audio -----------------

    def _record_fixed(self, seconds: float) -> np.ndarray:
        frames = int(seconds * SAMPLE_RATE)
        self.log.info(
            "[LucyVoicePipeline] Grabando audio fijo: %.1fs a %d Hz...",
            seconds,
            SAMPLE_RATE,
        )
        audio = sd.rec(
            frames,
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
        )
        sd.wait()
        self.log.info(
            "[LucyVoicePipeline] Audio grabado: %.2fs",
            len(audio) / SAMPLE_RATE,
        )
        # (frames, 1) -> (frames,)
        return audio.reshape(-1)

    # ----------------- ASR -----------------

    def _transcribe(self, audio: np.ndarray) -> Tuple[str, str]:
        """
        Transcribe audio en memoria usando Whisper.
        Devuelve (texto, idioma_detectado).
        """
        audio_f32 = audio.astype("float32")

        segments, info = self.whisper_model.transcribe(
            audio_f32,
            beam_size=1,
            vad_filter=False,
        )

        text_chunks = []
        for seg in segments:
            text_chunks.append(seg.text.strip())
        text = " ".join(t for t in text_chunks if t)

        lang = info.language or "unknown"
        self.log.info(
            "[LucyVoicePipeline] Texto reconocido: %r (lang=%s, p=%.2f)",
            text,
            lang,
            info.language_probability or 0.0,
        )
        return text, lang

    # ----------------- LLM (Ollama) -----------------

    def _extract_visible_answer(self, raw: str) -> str:
        """
        Extrae solo la parte 'visible' cuando el modelo devuelve
        trazas tipo 'Thinking...' y '...done thinking.'.
        """
        marker = "...done thinking."
        if marker in raw:
            visible = raw.split(marker, 1)[1].strip()
            if visible:
                return visible

        # Fallbacks por si el modelo usa otros prefijos
        for token in ["Respuesta:", "Answer:", "Final answer:", "Assistant:"]:
            if token in raw:
                tail = raw.split(token, 1)[1].strip()
                if tail:
                    return tail

        return raw

    def _call_ollama(self, prompt: str) -> str:
        """
        Llama al modelo local de Ollama via CLI (`ollama run`).
        Usamos CLI para simplificar dependencias.
        """
        self.log.info(
            "[LucyVoicePipeline] Llamando a Ollama (modelo=%s)...",
            self.config.ollama_model,
        )

        full_prompt = (
            "Sos Lucy, una asistente de voz local que habla en español rioplatense. "
            "Respondé de forma breve, oral, sin enumeraciones, sin explicar que sos un modelo. "
            "Usuario: " + prompt
        )

        try:
            proc = subprocess.run(
                ["ollama", "run", self.config.ollama_model],
                input=full_prompt.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.log.error(
                "Error al llamar a Ollama: %s\nstderr=%s",
                e,
                (e.stderr or b"").decode("utf-8", errors="ignore"),
            )
            return "Perdón, tuve un problema hablando con el modelo local."

        raw = proc.stdout.decode("utf-8", errors="ignore").strip()
        self.log.debug("[Ollama raw] %r", raw)

        clean = self._extract_visible_answer(raw)
        return clean

    # ----------------- TTS (Mimic3) -----------------

    def _speak(self, text: str) -> None:
        """
        Usa mimic3 por CLI:
            echo "texto" | mimic3 --voice es_ES/m-ailabs_low > out.wav
        y luego reproduce con sounddevice.
        """
        self.log.info(
            "[LucyVoicePipeline] Sintetizando audio con Mimic3 (voz=%s)...",
            self.config.tts_voice,
        )

        tmp_wav = Path("lucy_tts_output.wav")

        try:
            proc = subprocess.run(
                ["mimic3", "--voice", self.config.tts_voice],
                input=text.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.log.error(
                "Error en mimic3: %s\nstderr=%s",
                e,
                (e.stderr or b"").decode("utf-8", errors="ignore"),
            )
            return

        tmp_wav.write_bytes(proc.stdout)

        try:
            import soundfile as sf  # type: ignore

            data, sr = sf.read(str(tmp_wav), dtype="float32")
            sd.play(data, sr)
            sd.wait()
        except Exception as e:  # noqa: BLE001
            self.log.error("Error reproduciendo audio TTS: %s", e)
        finally:
            try:
                tmp_wav.unlink(missing_ok=True)
            except Exception:
                pass

    # ----------------- Roundtrip completo -----------------

    def run_mic_llm_roundtrip_once(self, duration_sec: Optional[float] = None) -> bool:
        """
        1. Graba audio 'duration_sec' segundos (o config.record_seconds).
        2. Transcribe con Whisper.
        3. Llama a Ollama.
        4. Responde con Mimic3.

        Devuelve True si el usuario dijo algo como "Lucy apagate".
        """
        seconds = float(duration_sec or self.config.record_seconds)

        audio = self._record_fixed(seconds)

        text, _lang = self._transcribe(audio)

        if not text.strip():
            self._speak("No llegué a escuchar nada claro.")
            return False

        lowered = text.lower()
        if "lucy apagate" in lowered or "apagate lucy" in lowered:
            self._speak("Bueno, me apago. Nos hablamos después.")
            return True

        reply = self._call_ollama(text)

        self.log.info("Lucy: %s", reply)
        self._speak(reply)

        return False


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )


def main() -> None:
    _setup_logging()
    main_log = logging.getLogger("LucyVoicePipelineMain")

    main_log.info(
        "Iniciando LucyVoicePipeline en modo texto+voz "
        "(push-to-talk simple, grabación fija)."
    )

    pipeline = LucyVoicePipeline()

    try:
        while True:
            input("Enter para grabar (Ctrl+C para salir)...")
            should_stop = pipeline.run_mic_llm_roundtrip_once()
            if should_stop:
                main_log.info("Lucy pidió apagarse por voz. Terminando.")
                break
    except KeyboardInterrupt:
        main_log.info("Interrupción por teclado. Chau.")


if __name__ == "__main__":
    main()
PYEOF

echo "Listo: lucy_voice/pipeline_lucy_voice.py actualizado para esconder el 'Thinking...'."
