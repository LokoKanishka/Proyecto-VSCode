"""
pipecat_processors.py

Procesadores Pipecat específicos de Lucy.

En esta primera versión definimos un procesador de texto que:
- Recibe TextFrames con texto del usuario.
- Llama al LLM local vía Ollama.
- Empuja un nuevo TextFrame con la respuesta de Lucy.

Todavía no está enchufado al pipeline principal; eso lo haremos
en pasos siguientes desde `pipecat_graph.py`.
"""

from __future__ import annotations

from typing import Any
import subprocess

from loguru import logger

from pipecat.frames.frames import Frame, TextFrame
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor


class LucyOllamaTextLLMProcessor(FrameProcessor):
    """
    Procesador de texto → LLM local (Ollama) para Lucy.

    Uso esperado en el futuro:
        - Recibe TextFrame con texto de usuario (FrameDirection.DOWNSTREAM).
        - Llama a Ollama con un prompt estilo "Lucy".
        - Empuja un nuevo TextFrame con la respuesta del modelo.
    """

    def __init__(self, model: str = "gpt-oss:20b") -> None:
        super().__init__()
        self.model = model

    def _build_prompt(self, user_text: str) -> str:
        """
        Arma el prompt que se manda al modelo de Ollama, usando
        el mismo estilo de Lucy que ya usamos en el pipeline actual.
        """
        system_prompt = (
            "Actuá como Lucy, un asistente de voz local que corre en una PC con Linux. "
            "Respondé en castellano rioplatense, en una o pocas frases claras, "
            "sin enumeraciones largas ni formato raro."
        )

        prompt = (
            f"{system_prompt}\n\n"
            f"Usuario: {user_text}\n"
            f"Lucy:"
        )
        return prompt

    def _call_ollama(self, prompt: str) -> str:
        """
        Llama al modelo local en Ollama usando la CLI.

        Devuelve el texto crudo que sale por stdout.
        """
        cmd = ["ollama", "run", self.model, prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            logger.error(
                "[LucyOllamaTextLLMProcessor] No se encontró el comando 'ollama'. "
                "Asegurate de que Ollama esté instalado y en el PATH."
            )
            return "[Lucy] No encuentro el servicio local de modelo (Ollama)."

        except subprocess.CalledProcessError as e:
            stderr = (e.stderr or "").strip()
            logger.error(
                "[LucyOllamaTextLLMProcessor] Error al ejecutar ollama con el modelo {}: {}",
                self.model,
                stderr,
            )
            return "[Lucy] Hubo un error al hablar con el modelo local."

        return (result.stdout or "").strip()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        """
        Procesa cada frame que pasa por el pipeline.

        - Si no es un TextFrame, simplemente lo deja seguir.
        - Si es TextFrame y va DOWNSTREAM, lo trata como texto de usuario.
        """
        # Llamamos primero a la implementación base (manejo interno de Pipecat).
        await super().process_frame(frame, direction)

        # Sólo queremos tocar texto que va "hacia abajo" en el pipeline.
        if direction is not FrameDirection.DOWNSTREAM:
            await self.push_frame(frame, direction)
            return

        if not isinstance(frame, TextFrame):
            # No es texto: lo dejamos pasar sin cambios.
            await self.push_frame(frame, direction)
            return

        user_text = (getattr(frame, "text", "") or "").strip()
        if not user_text:
            # Texto vacío: lo reenviamos y listo.
            await self.push_frame(frame, direction)
            return

        logger.info(
            "[LucyOllamaTextLLMProcessor] Recibí texto del usuario: {}",
            user_text,
        )

        prompt = self._build_prompt(user_text)
        answer = self._call_ollama(prompt)

        if not answer:
            answer = "[Lucy] No pude generar una respuesta."

        logger.info(
            "[LucyOllamaTextLLMProcessor] Respuesta generada por el modelo local (recortada a log): {}",
            answer[:200],
        )
class LucyWhisperASRProcessor(FrameProcessor):
    """
    Esqueleto de processor de ASR para Lucy usando faster-whisper.

    Objetivo futuro:
        - Recibir frames de audio (cuando definamos el tipo de frame de audio
          que vamos a usar en el pipeline).
        - Acumular audio hasta tener un fragmento completo.
        - Pasar ese audio por faster-whisper.
        - Emitir un TextFrame con la transcripcion.

    Por ahora, este processor es un stub que solo deja pasar todos los frames
    tal como llegan, sin modificar nada. Sirve como punto de partida para
    integrar el ASR dentro de Pipecat.
    """

    def __init__(self, model_size: str = "small", language: str = "es") -> None:
        super().__init__()
        self.model_size = model_size
        self.language = language
        # Mas adelante: inicializar aca el modelo de faster-whisper
        # y buffers de audio, etc.

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        # Llamamos primero a la logica base de Pipecat
        await super().process_frame(frame, direction)

        # TODO (futuro):
        # - Si el frame es de audio y va en la direccion correcta,
        #   acumularlo en un buffer.
        # - Cuando se detecte fin de segmento (o VAD), correr faster-whisper
        #   y generar un TextFrame con la transcripcion.

        # Por ahora, este stub solo deja pasar el frame sin tocarlo.
        await self.push_frame(frame, direction)
