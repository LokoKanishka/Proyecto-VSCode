"""
Lucy voz – Fase 2: pipeline base con Pipecat, LLM local y pruebas de ASR y TTS.
Este módulo define:
Este módulo define:

- Una estructura de pipeline pensada para Pipecat (a futuro).
- Un camino de texto: recibe una frase, la pasa a un LLM local (Ollama)
  y devuelve la respuesta, sin audio.
- Un modo chat interactivo en consola (solo texto).
- Un camino de audio: micrófono → WAV → ASR (faster-whisper) → texto.
- Un roundtrip completo: voz → texto → LLM → texto → TTS (Mimic3).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional
from loguru import logger


import subprocess
import textwrap
from pathlib import Path
import wave

import sounddevice as sd
from faster_whisper import WhisperModel
from lucy_voice.pipecat_graph import build_lucy_pipeline




try:
    import pipecat  # noqa: F401  # solo para comprobar que la librería existe
except ImportError:  # pragma: no cover - en caso de que no esté instalado
    pipecat = None


@dataclass
class LucyPipelineConfig:
    """
    Configuración mínima del pipeline de Lucy voz.
    """
    asr_model: str = "faster-whisper-small"
    asr_model_size: str = "small"
    asr_samplerate: int = 16000
    tts_voice: str = "es_ES/m-ailabs_low"  # voz castellana Mimic3 (la que ya sabemos que se escucha)
    llm_model: str = "gpt-oss:20b"       # modelo pesado por defecto en Ollama


class LucyVoicePipeline:
    """
    Orquestador de alto nivel del pipeline de Lucy.
    """

    def __init__(self, config: Optional[LucyPipelineConfig] = None) -> None:
        self.config = config or LucyPipelineConfig()
        # Acá más adelante se va a construir el grafo de Pipecat
        self._graph: Any = None

    # -------------------------------------------------------------------------
    # Bloque futuro: grafo de Pipecat
    # -------------------------------------------------------------------------
    def build_graph(self) -> None:
        """
        Construye el grafo de Pipecat de Lucy.

        Por ahora delega en el stub `build_lucy_pipeline()`, que devuelve
        un Pipeline vacío. En próximos pasos vamos a ir llenando ese Pipeline
        con los procesadores reales (STT, LLM, TTS, etc.).
        """
        logger.info("[LucyVoicePipeline] build_graph(): usando stub build_lucy_pipeline()…")

        pipeline = build_lucy_pipeline(self.config)

        # Lo guardamos en la instancia para usarlo más adelante.
        self._graph = pipeline

        logger.info(
        "[LucyVoicePipeline] build_graph(): pipeline (stub) creado correctamente: %r",
        pipeline,
        )

    def start(self) -> None:
        """
        Punto de entrada para arrancar el pipeline "real" (cuando exista el grafo).
        """
        if self._graph is None:
            print("[LucyVoicePipeline] start(): no hay grafo definido todavía.")
            return

        if self._graph == "PENDING_IMPLEMENTATION":
            print("[LucyVoicePipeline] start(): el grafo está marcado como PENDING_IMPLEMENTATION.")
            return

        print("[LucyVoicePipeline] start(): pipeline real aún no está implementado.")

    def stop(self) -> None:
        """
        Detiene el pipeline y libera recursos.
        """
        print("[LucyVoicePipeline] stop(): nada que detener todavía (esqueleto).")

    # -------------------------------------------------------------------------
    # Bloque actual: texto → LLM local → texto (sin audio)
    # -------------------------------------------------------------------------
    def _query_llm_with_ollama(self, prompt: str) -> str:
        """
        Llama al modelo local en Ollama usando la CLI.

        Usa el modelo configurado en self.config.llm_model (por defecto gpt-oss:20b).
        """
        model = self.config.llm_model
        cmd = ["ollama", "run", model, prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "No se encontró el comando 'ollama'. "
                "Asegurate de que Ollama está instalado y en el PATH."
            ) from None
        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            raise RuntimeError(
                f"Error al ejecutar ollama con el modelo {model}: {stderr}"
            ) from None

        # La CLI de ollama devuelve el texto directamente en stdout.
        return result.stdout.strip()

    def _visible_answer(self, full_text: str) -> str:
        """
        Recibe el texto completo devuelto por el LLM y devuelve sólo la frase
        final que queremos que Lucy diga y que se vea en consola.
        """
        if not full_text:
            return ""

        text = full_text.strip()

        # Partimos en líneas y nos quedamos con las que no estén vacías
        lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
        if not lines:
            return ""

        # En la práctica casi siempre queremos la última línea
        candidate = lines[-1]

        # Si esa línea es demasiado cortita (por ejemplo "Ok.")
        # y hay otra anterior, usamos la anterior.
        if len(candidate) < 5 and len(lines) >= 2:
            candidate = lines[-2]

        return candidate


    def run_text_roundtrip(self, user_text: str) -> str:
        """
        Ejecuta un "roundtrip" simple: texto de usuario → LLM local → texto de respuesta.
        """
        system_prompt = (
            "Actuá como Lucy, un asistente de voz local que corre en una PC con Linux. "
            "Respondé en castellano rioplatense, en una o pocas frases claras, "
            "sin enumeraciones largas ni formato raro."
        )

        prompt = textwrap.dedent(
            f"""\
            {system_prompt}

            Usuario: {user_text}
            Lucy:"""
        )

        full_answer = self._query_llm_with_ollama(prompt)
        visible = self._visible_answer(full_answer)

        print("[LucyVoicePipeline] Usuario:", user_text)
        print("[LucyVoicePipeline] Lucy:", visible)

        return full_answer

    # -------------------------------------------------------------------------
    # Bloque nuevo: texto → TTS (Mimic 3) → audio
    # -------------------------------------------------------------------------
    def _speak_with_tts(self, text: str) -> None:
        """
        Sintetiza `text` con Mimic 3 usando la voz configurada
        y reproduce el audio con `aplay`.
        """
        if not text:
            return

        try:
            import tempfile
            import subprocess
            from pathlib import Path

            # Archivo WAV temporal
            tmp_dir = Path(tempfile.gettempdir())
            wav_path = tmp_dir / "lucy_tts_runtime.wav"

            # Comando Mimic 3: va a leer el texto desde stdin
            cmd_mimic3 = [
                "mimic3",
                "--voice",
                self.config.tts_voice,
                "--stdout",
            ]

            # Generamos el WAV enviando el texto por stdin (como el echo | mimic3)
            with wav_path.open("wb") as f:
                subprocess.run(
                    cmd_mimic3,
                    input=text.encode("utf-8"),
                    stdout=f,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )

            # Reproducimos el WAV con aplay
            subprocess.run(["aplay", "-q", str(wav_path)], check=False)

        except Exception as exc:
            print(f"[LucyVoicePipeline] [TTS] Error al sintetizar o reproducir: {exc}")


    # -------------------------------------------------------------------------
    # Bloque actual: audio → ASR (faster-whisper) → texto (sin LLM)
    # -------------------------------------------------------------------------
    def _record_mic_to_wav(self, duration_sec: float = 5.0) -> Path:
        """
        Graba audio desde el micrófono y devuelve la ruta de un WAV temporal.

        Usa:
        - 1 canal (mono)
        - frecuencia de muestreo tomada de self.config.asr_samplerate
        - formato 16-bit PCM
        """
        samplerate = self.config.asr_samplerate
        print(f"[LucyVoicePipeline] Grabando {duration_sec} segundos a {samplerate} Hz…")

        try:
            audio = sd.rec(
                int(duration_sec * samplerate),
                samplerate=samplerate,
                channels=1,
                dtype="int16",
            )
            sd.wait()
        except sd.PortAudioError as exc:  # noqa: BLE001
            print(f"[LucyVoicePipeline] [ERROR] No se pudo acceder al micrófono: {exc}")
            raise RuntimeError("Error de dispositivo de audio") from exc

        # Guardamos el WAV en la carpeta tests para reutilizarlo si hace falta
        wav_path = Path(__file__).resolve().parent / "tests" / "mic_test_input_from_pipeline.wav"
        with wave.open(str(wav_path), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)  # 16-bit -> 2 bytes
            wf.setframerate(samplerate)
            wf.writeframes(audio.tobytes())

        print(f"[LucyVoicePipeline] Audio guardado en: {wav_path}")
        return wav_path

    def _asr_transcribe_wav(self, audio_path: Path):
        """
        Usa faster-whisper para transcribir el archivo WAV dado.

        Devuelve (segments, info), igual que en el test `test_asr_from_tts.py`.
        """
        model_size = self.config.asr_model_size
        print(f"[LucyVoicePipeline] Cargando modelo ASR: {model_size}")

        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        segments, info = model.transcribe(str(audio_path), language="es")
        return segments, info

    def run_mic_to_text_once(self, duration_sec: float = 5.0) -> None:
        """
        Ejecuta un ciclo simple:
            micrófono → WAV → ASR → texto por consola.
        """
        try:
            wav_path = self._record_mic_to_wav(duration_sec=duration_sec)
        except RuntimeError:
            # Ya se imprimió el mensaje de error en _record_mic_to_wav
            return

        print("\n[LucyVoicePipeline] == Prueba ASR desde micrófono (pipeline) ==")
        print(f"[LucyVoicePipeline] Archivo de audio: {wav_path}")

        try:
            segments, info = self._asr_transcribe_wav(wav_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[LucyVoicePipeline] [ERROR] Falló la transcripción: {exc}")
            return

        print(
            f"[LucyVoicePipeline] Idioma detectado: "
            f"{info.language} (confianza: {info.language_probability:.2f})"
        )
        print("[LucyVoicePipeline] Texto reconocido:")
        for seg in segments:
            text = getattr(seg, "text", "").strip()
            if text:
                print(f"- {text}")

    # -------------------------------------------------------------------------
    # Bloque actual: roundtrip voz → texto → LLM → texto → TTS
    # -------------------------------------------------------------------------
    def run_mic_llm_roundtrip_once(self, duration_sec: float = 5.0) -> bool:
        """
        Ciclo completo de prueba en el pipeline:

            voz (micrófono) → texto (ASR) → LLM local → respuesta de Lucy (texto) → TTS.

        Devuelve:
            True  si debe detenerse el loop de voz (comando "Lucy desactivate").
            False en cualquier otro caso.
        """
        # 0) Grabar audio del micrófono
        try:
            wav_path = self._record_mic_to_wav(duration_sec=duration_sec)
        except RuntimeError:
            # El error de audio ya se mostró en _record_mic_to_wav
            return False

        print("\n[LucyVoicePipeline] == Roundtrip voz → texto → LLM (pipeline) ==")
        print(f"[LucyVoicePipeline] Archivo de audio: {wav_path}")

        # 1) ASR: convertir voz en texto
        try:
            segments, info = self._asr_transcribe_wav(wav_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[LucyVoicePipeline] [ERROR] Falló la transcripción: {exc}")
            return False

        user_text = " ".join(
            getattr(seg, "text", "").strip() for seg in segments
            if getattr(seg, "text", "").strip()
        )

        if not user_text:
            print("[LucyVoicePipeline] No se reconoció texto en el audio.")
            return False

        print(
            f"[LucyVoicePipeline] Idioma detectado: "
            f"{info.language} (confianza: {info.language_probability:.2f})"
        )
        print(f"[LucyVoicePipeline] Texto reconocido (usuario): {user_text!r}")

        # 2a) Comando especial de apagado por voz
        lowered = user_text.lower()
        normalized = lowered.replace(" ", "")

        if (
            "lucy desactivate" in lowered
            or "lucy deactivate" in lowered
            or "lucydesactivate" in normalized
            or "lucydesactivar" in normalized
            or "lucydesactívate" in normalized
        ):
            visible_answer = (
                "Ok, me desactivo por ahora. Si querés volver a hablar conmigo, "
                "volvé a abrir Lucy voz."
            )
            print(f"[LucyVoicePipeline] Lucy (apagado): {visible_answer}")
            self._speak_with_tts(visible_answer)
            print(
                f"[LucyVoicePipeline] Respuesta de Lucy (apagado por voz): "
                f"{visible_answer!r}"
            )
            return True

        # 2b) LLM: pasar ese texto por el modelo local en Ollama
        try:
            answer = self.run_text_roundtrip(user_text)
        except RuntimeError as e:
            print(f"[LucyVoicePipeline] [ERROR] Falló la llamada al LLM: {e}")
            return False

        # 3) TTS: decir la respuesta en voz (si Mimic 3 está disponible)
        visible_answer = self._visible_answer(answer)
        print(f"[LucyVoicePipeline] Lucy: {visible_answer}")
        print("[LucyVoicePipeline] TTS: generando audio con Mimic 3…")
        self._speak_with_tts(visible_answer)

        # Resumen consistente con lo que se dijo en voz
        print(f"[LucyVoicePipeline] Respuesta de Lucy (roundtrip voz→LLM): {visible_answer!r}")

        return False


    # -------------------------------------------------------------------------
    # Modo chat interactivo en consola (sólo texto)
    # -------------------------------------------------------------------------
    def interactive_loop(self) -> None:
        """
        Bucle simple de chat en consola con Lucy usando el LLM local.

        Esto es útil como "simulador" del pipeline antes de conectar audio real.
        """
        print("Lucy voz (modo texto). Escribí 'salir' para terminar.\n")

        while True:
            try:
                user = input("Vos: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[LucyVoicePipeline] Fin de la sesión.")
                break

            if user.lower() in {"salir", "exit", "quit"}:
                print("[LucyVoicePipeline] Chau, hasta luego 💜")
                break

            if not user:
                continue

            try:
                self.run_text_roundtrip(user)
            except RuntimeError as e:
                print(f"[LucyVoicePipeline] Error: {e}")
                break


def main() -> None:
    """
    Punto de entrada para pruebas manuales:

        python -m lucy_voice.pipeline_lucy_voice
    """
    pipeline = LucyVoicePipeline()
    pipeline.build_graph()  # deja el marcador de grafo pendiente
    pipeline.interactive_loop()


if __name__ == "__main__":
    main()


