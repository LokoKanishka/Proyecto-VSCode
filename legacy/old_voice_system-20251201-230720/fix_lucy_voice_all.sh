#!/usr/bin/env bash
set -euo pipefail

echo "== Lucy Voice: script de reparación y mejoras =="

# Detectar raíz del repo (carpeta donde está este script)
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d "lucy_voice" ]; then
  echo "ERROR: No se encontró la carpeta 'lucy_voice' en: $ROOT_DIR"
  echo "Corré este script desde la raíz del proyecto Proyecto-VSCode."
  exit 1
fi

TIMESTAMP="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="lucy_voice_backup_${TIMESTAMP}"

echo ">> Haciendo backup de lucy_voice/ en: ${BACKUP_DIR}"
cp -a lucy_voice "${BACKUP_DIR}"

echo ">> Asegurando carpeta de tests..."
mkdir -p lucy_voice/tests

###############################################################################
# 1) pipeline_lucy_voice.py — pipeline de voz más robusto, con VAD simple
###############################################################################
cat > lucy_voice/pipeline_lucy_voice.py << 'EOF'
from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from typing import Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


@dataclass
class LucyPipelineConfig:
    """Configuración del pipeline de voz de Lucy.

    Ajustá estos valores en un solo lugar si querés cambiar modelo ASR, voz TTS, etc.
    """

    # ASR / Whisper
    asr_model: str = "small"         # nombre del modelo de faster-whisper
    asr_device: str = "cpu"          # "cpu" o "cuda"
    asr_compute_type: str = "int8"   # "int8", "int8_float16", etc.

    # Audio de entrada
    sample_rate: int = 16000
    max_record_seconds: float = 5.0

    # VAD sencillo basado en energía
    vad_enabled: bool = True
    vad_energy_threshold: float = 0.015
    vad_silence_duration: float = 0.7  # segundos de silencio continuo antes de cortar

    # LLM / Ollama
    ollama_model: str = "gpt-oss:20b"
    # temperatura: la CLI de ollama no expone flag oficial aquí,
    # por lo que se usa la configuración del modelo/modelfile.

    # TTS / Mimic3
    tts_voice: str = "es_ES/m-ailabs_low"
    tts_command: str = "mimic3"
    tts_player: str = "aplay"


class LucyVoicePipeline:
    """Pipeline de voz de Lucy: micrófono → ASR → LLM (Ollama) → TTS (Mimic3)."""

    _whisper_model: Optional[WhisperModel] = None

    def __init__(
        self,
        config: Optional[LucyPipelineConfig] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.config = config or LucyPipelineConfig()
        self.log = logger or logging.getLogger(self.__class__.__name__)

        if LucyVoicePipeline._whisper_model is None:
            self.log.info(
                "Cargando modelo Whisper '%s' (device=%s, compute_type=%s)...",
                self.config.asr_model,
                self.config.asr_device,
                self.config.asr_compute_type,
            )
            LucyVoicePipeline._whisper_model = WhisperModel(
                self.config.asr_model,
                device=self.config.asr_device,
                compute_type=self.config.asr_compute_type,
            )

    # --------------------------------------------------------------------- #
    # 1) Entrada de audio (micrófono) con VAD simple
    # --------------------------------------------------------------------- #
    def _record_mic_to_wav(self, path: str) -> None:
        """Graba desde el micrófono en path (WAV 16 kHz mono int16) con VAD simple."""
        cfg = self.config
        sr = cfg.sample_rate
        max_frames = int(sr * cfg.max_record_seconds)
        chunk = int(sr * 0.10)  # 100 ms

        self.log.info(
            "[LucyVoicePipeline] Grabando audio (máx %.1fs, VAD=%s)...",
            cfg.max_record_seconds,
            cfg.vad_enabled,
        )

        frames = []
        with sd.InputStream(samplerate=sr, channels=1, dtype="float32") as stream:
            num_silence_chunks = 0
            max_silence_chunks = int(cfg.vad_silence_duration / (chunk / sr)) or 1
            total_frames = 0

            while total_frames < max_frames:
                data, _ = stream.read(chunk)
                if data.size == 0:
                    break

                frames.append(data.copy())
                total_frames += data.shape[0]

                if cfg.vad_enabled:
                    energy = float(np.mean(np.abs(data)))
                    self.log.debug("VAD energía=%.5f", energy)
                    if energy < cfg.vad_energy_threshold:
                        num_silence_chunks += 1
                        if (
                            num_silence_chunks >= max_silence_chunks
                            and total_frames > int(sr * 0.8)
                        ):
                            self.log.debug(
                                "VAD: silencio prolongado detectado, deteniendo grabación."
                            )
                            break
                    else:
                        num_silence_chunks = 0

        if not frames:
            self.log.warning(
                "[LucyVoicePipeline] No se capturó audio, generando 0.1s de silencio."
            )
            audio = np.zeros((int(sr * 0.1), 1), dtype=np.float32)
        else:
            audio = np.concatenate(frames, axis=0)

        audio_int16 = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)

        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(audio_int16.tobytes())

        self.log.info(
            "[LucyVoicePipeline] Audio grabado: %.2fs", audio_int16.shape[0] / sr
        )

    # --------------------------------------------------------------------- #
    # 2) ASR / Whisper
    # --------------------------------------------------------------------- #
    def _asr_transcribe_wav(self, path: str) -> str:
        """Transcribe un WAV usando faster-whisper."""
        model = LucyVoicePipeline._whisper_model
        if model is None:
            raise RuntimeError("Modelo Whisper no inicializado.")

        self.log.info("[LucyVoicePipeline] Transcribiendo audio con Whisper...")
        segments, info = model.transcribe(path, beam_size=5)
        self.log.info(
            "Idioma detectado: %s (confianza %.2f)",
            info.language,
            info.language_probability,
        )

        texts = []
        for segment in segments:
            self.log.debug(
                "[ASR] %.2f-%.2f: %s", segment.start, segment.end, segment.text
            )
            texts.append(segment.text.strip())

        full_text = " ".join(texts).strip()
        self.log.info("[LucyVoicePipeline] Texto reconocido: %r", full_text)
        return full_text

    # --------------------------------------------------------------------- #
    # 3) LLM / Ollama
    # --------------------------------------------------------------------- #
    def _system_prompt(self) -> str:
        """Prompt de sistema para Lucy (persona básica)."""
        return (
            "Sos Lucy, un asistente de voz local que habla en castellano rioplatense. "
            "Respondés de manera breve, clara y oral (como si hablaras), sin enumerar "
            "opciones salvo que te lo pidan. No expliques que sos un modelo de lenguaje."
        )

    def _visible_answer(self, raw: str) -> str:
        """Filtra la salida cruda del modelo antes de hablarla / mostrarla."""
        # Si en el futuro usás modelos tipo DeepSeek-R1, acá podés filtrar <think>...</think>
        return raw.strip()

    def run_text_roundtrip(self, user_text: str, timeout: float = 120.0) -> str:
        """Envía texto a Ollama y devuelve la respuesta (como string)."""
        cfg = self.config
        prompt = f"{self._system_prompt()}\n\nUsuario: {user_text}\nLucy:"

        cmd = [
            "ollama",
            "run",
            cfg.ollama_model,
            prompt,
        ]

        self.log.info("[LucyVoicePipeline] Llamando a Ollama (%s)...", cfg.ollama_model)

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
                text=True,
            )
        except FileNotFoundError:
            self.log.error(
                "No se encontró el comando 'ollama'. ¿Está instalado y en el PATH?"
            )
            return (
                "No puedo pensar ahora mismo porque falta Ollama en este sistema. "
                "Revisá la instalación y el servicio."
            )
        except subprocess.TimeoutExpired:
            self.log.error("Timeout esperando respuesta del LLM (Ollama).")
            return (
                "Me colgué pensando la respuesta y tardé demasiado, perdón. "
                "Probemos de nuevo con algo más corto."
            )

        if proc.returncode != 0:
            self.log.error(
                "Error ejecutando 'ollama run' (código %s): %s",
                proc.returncode,
                proc.stderr.strip(),
            )
            return (
                "No pude conectar con mi modelo local de pensamiento. "
                "Revisá que Ollama esté corriendo y que el modelo esté instalado."
            )

        raw = proc.stdout or ""
        self.log.debug("[Ollama raw] %r", raw)
        return self._visible_answer(raw)

    # --------------------------------------------------------------------- #
    # 4) TTS / Mimic3
    # --------------------------------------------------------------------- #
    def _speak_with_tts(self, text: str) -> None:
        """Convierte texto a habla con Mimic3 y lo reproduce con aplay (u otro)."""
        if not text or not text.strip():
            self.log.warning("[LucyVoicePipeline] Texto TTS vacío, no hablo.")
            return

        cfg = self.config
        self.log.info(
            "[LucyVoicePipeline] Sintetizando audio con Mimic3 (voz=%s)...",
            cfg.tts_voice,
        )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name

        try:
            tts_cmd = [
                cfg.tts_command,
                "--voice",
                cfg.tts_voice,
                "--stdout",
            ]

            try:
                proc = subprocess.run(
                    tts_cmd,
                    input=text.encode("utf-8"),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=60.0,
                    check=False,
                )
            except FileNotFoundError:
                self.log.error(
                    "No se encontró el comando '%s'. ¿Instalaste Mimic3?",
                    cfg.tts_command,
                )
                return
            except subprocess.TimeoutExpired:
                self.log.error("Timeout en Mimic3 al generar audio.")
                return

            if proc.returncode != 0 or not proc.stdout:
                self.log.error(
                    "Error en Mimic3 (código %s): %s",
                    proc.returncode,
                    proc.stderr.decode("utf-8", errors="ignore"),
                )
                return

            with open(wav_path, "wb") as wf:
                wf.write(proc.stdout)

            self.log.info("[LucyVoicePipeline] Reproduciendo respuesta...")
            try:
                subprocess.run(
                    [cfg.tts_player, wav_path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60.0,
                    check=False,
                )
            except FileNotFoundError:
                self.log.error(
                    "No se encontró el comando de reproducción '%s'.", cfg.tts_player
                )
            except subprocess.TimeoutExpired:
                self.log.error(
                    "Timeout reproduciendo audio con '%s'.", cfg.tts_player
                )
        finally:
            try:
                os.unlink(wav_path)
            except OSError:
                pass

    # --------------------------------------------------------------------- #
    # 5) Lógica de apagado por voz
    # --------------------------------------------------------------------- #
    def _is_shutdown_command(self, text: str) -> bool:
        """Detecta frases de apagado del estilo 'Lucy, apagate'."""
        normalized = text.lower().strip()

        shutdown_phrases = [
            "lucy desactivate",
            "lucy desactivarse",
            "lucy desactivarte",
            "lucy desactivar",
            "lucy desactívate",
            "lucy apagarse",
            "lucy apagarte",
            "lucy apagate",
            "apagate lucy",
            "lucy chau",
            "chau lucy",
        ]

        return any(phrase in normalized for phrase in shutdown_phrases)

    # --------------------------------------------------------------------- #
    # 6) Roundtrip principal (mic → texto → LLM → TTS)
    # --------------------------------------------------------------------- #
    def run_mic_llm_roundtrip_once(self, duration_sec: Optional[float] = None) -> bool:
        """Hace un roundtrip completo y devuelve True si se pidió apagar a Lucy.

        Mantengo el nombre del parámetro `duration_sec` para compatibilidad con
        código existente (por ej. wakeword_iddkd.py).
        """
        wav_path = os.path.join(tempfile.gettempdir(), "lucy_mic_input.wav")

        old_max = self.config.max_record_seconds
        if duration_sec is not None:
            self.config.max_record_seconds = duration_sec

        try:
            self._record_mic_to_wav(wav_path)
            user_text = self._asr_transcribe_wav(wav_path)
        finally:
            self.config.max_record_seconds = old_max
            try:
                os.unlink(wav_path)
            except OSError:
                pass

        if not user_text.strip():
            self.log.info("[LucyVoicePipeline] No escuché nada (texto vacío).")
            return False

        if self._is_shutdown_command(user_text):
            farewell = (
                "Listo, me quedo callada por ahora. "
                "Cuando quieras volvemos a hablar."
            )
            self.log.info("[LucyVoicePipeline] Comando de apagado por voz detectado.")
            self._speak_with_tts(farewell)
            return True

        answer = self.run_text_roundtrip(user_text)
        self.log.info("Lucy: %s", answer)
        self._speak_with_tts(answer)
        return False


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )
    log = logging.getLogger("LucyVoicePipelineMain")
    log.info("Iniciando LucyVoicePipeline en modo texto+voz (push-to-talk simple).")

    pipeline = LucyVoicePipeline()

    try:
        while True:
            input("Enter para grabar (Ctrl+C para salir)...")
            should_stop = pipeline.run_mic_llm_roundtrip_once()
            if should_stop:
                log.info("Lucy pidió apagarse. Saliendo.")
                break
    except KeyboardInterrupt:
        log.info("Interrupción por teclado. Chau.")


if __name__ == "__main__":
    main()
EOF

echo ">> Actualizado lucy_voice/pipeline_lucy_voice.py"

###############################################################################
# 2) wakeword_iddkd.py — corrección del bug de apagado + uso correcto de OWW
###############################################################################
cat > lucy_voice/wakeword_iddkd.py << 'EOF'
from __future__ import annotations

import logging
import time

import numpy as np
import sounddevice as sd
from openwakeword.model import Model

from .pipeline_lucy_voice import LucyPipelineConfig, LucyVoicePipeline

# Parámetros de audio / wake word
SAMPLE_RATE = 16000
FRAME_SIZE = 1280  # 80 ms a 16 kHz
THRESHOLD = 0.5    # umbral base de openWakeWord
REQUIRED_HITS = 3  # cantidad de frames consecutivos por encima del umbral
COOLDOWN_SECONDS = 1.0  # tiempo mínimo entre activaciones válidas


def _listen_for_wake_word(model: Model, logger: logging.Logger) -> None:
    """Bloquea hasta detectar el wake word usando openWakeWord."""
    logger.info(
        "Esperando wake word (openWakeWord, frame=%d, threshold=%.2f)...",
        FRAME_SIZE,
        THRESHOLD,
    )

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="int16",
        blocksize=FRAME_SIZE,
    ) as stream:
        consecutive_hits = 0
        last_detection_time = 0.0

        while True:
            audio, _ = stream.read(FRAME_SIZE)
            if audio.size == 0:
                continue

            # audio: shape (FRAME_SIZE, 1) int16 → 1D
            audio_int16 = audio.reshape(-1)

            prediction = model.predict(audio_int16)

            # Intentamos primero claves típicas de OWW; como fallback usamos el máximo
            score_jarvis = max(
                float(prediction.get("hey_jarvis", 0.0)),
                float(prediction.get("hey jarvis", 0.0)),
            )
            score = score_jarvis if score_jarvis > 0.0 else float(
                max(prediction.values()) if prediction else 0.0
            )

            logger.debug("OWW score=%.3f", score)

            if score >= THRESHOLD:
                consecutive_hits += 1
            else:
                consecutive_hits = max(0, consecutive_hits - 1)

            if consecutive_hits >= REQUIRED_HITS:
                now = time.time()
                if now - last_detection_time >= COOLDOWN_SECONDS:
                    logger.info(
                        "Wake word detectada (score=%.3f, hits=%d).",
                        score,
                        consecutive_hits,
                    )
                    last_detection_time = now
                    return
                else:
                    logger.debug(
                        "Wake word en cooldown (%.2fs)...",
                        now - last_detection_time,
                    )
                    consecutive_hits = 0


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(name)s:%(lineno)d - %(message)s",
    )
    logger = logging.getLogger("LucyWakeWord")

    logger.info("Iniciando detección de wake word con openWakeWord...")
    logger.info(
        "Decí algo como 'hey jarvis' cerca del micrófono para activar a Lucy."
    )

    # Instanciamos el modelo de wake word (uso default de OWW)
    oww_model = Model(inference_framework="onnx")

    # Pipeline de Lucy (ASR + LLM + TTS)
    pipeline = LucyVoicePipeline(LucyPipelineConfig())

    try:
        while True:
            _listen_for_wake_word(oww_model, logger)

            logger.info("Wake word detectada. Iniciando roundtrip de Lucy...")
            # IMPORTANTE: ahora respetamos el valor de retorno
            should_stop = pipeline.run_mic_llm_roundtrip_once(duration_sec=5.0)

            if should_stop:
                logger.info(
                    "Lucy pidió apagarse (comando de voz). "
                    "Saliendo del modo wake word."
                )
                break

            logger.info(
                "Roundtrip finalizado. Volviendo a escuchar el wake word..."
            )

    except KeyboardInterrupt:
        logger.info("Interrupción por teclado (Ctrl+C). Saliendo.")


if __name__ == "__main__":
    main()
EOF

echo ">> Actualizado lucy_voice/wakeword_iddkd.py"

###############################################################################
# 3) Test de humo mínimo para Ollama + pipeline
###############################################################################
cat > lucy_voice/tests/test_ollama_roundtrip_basic.py << 'EOF'
import pytest

from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline, LucyPipelineConfig


@pytest.mark.slow
def test_ollama_roundtrip_basico():
    """Smoke test muy simple para el pipeline texto→LLM.

    No valida el contenido, sólo que:
      - Se puede instanciar el pipeline
      - Llamar a run_text_roundtrip() no revienta
      - Devuelve un string no vacío

    Si Ollama no está instalado o el modelo no existe, el pipeline devuelve
    un mensaje de error legible, pero el test igualmente pasa (es un test
    de estabilidad, no de entorno).
    """
    cfg = LucyPipelineConfig()
    pipeline = LucyVoicePipeline(cfg)

    respuesta = pipeline.run_text_roundtrip(
        "Decime una frase muy corta para probar que estás viva."
    )

    assert isinstance(respuesta, str)
    assert respuesta.strip()
EOF

echo ">> Creado lucy_voice/tests/test_ollama_roundtrip_basic.py"

echo
echo "== Listo =="
echo "Se hizo backup de lucy_voice/ en: ${BACKUP_DIR}"
echo
echo "Sugerencias de prueba:"
echo "  1) Activar el entorno:  source .venv-lucy-voz/bin/activate"
echo "  2) Probar pipeline texto+voz:  python -m lucy_voice.pipeline_lucy_voice"
echo "  3) Probar wake word:          python -m lucy_voice.wakeword_iddkd"
echo "  4) Correr tests de humo:      pytest lucy_voice/tests/test_ollama_roundtrip_basic.py"
echo
echo "Si algo no te gusta, podés comparar con el backup ${BACKUP_DIR} (git diff, meld, etc.)."
EOF

---

## 2. Cómo usarlo (paso real en tu máquina)

1. Guardá el archivo en la raíz del repo:  
   `Proyecto-VSCode/fix_lucy_voice_all.sh`

2. Dalo permisos de ejecución:

   ```bash
   cd ~/Lucy_Workspace/Proyecto-VSCode
   chmod +x fix_lucy_voice_all.sh
