import asyncio
import logging
from typing import Optional

from src.core.base_worker import BaseWorker
from src.core.lucy_types import LucyMessage, MessageType
from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.audio import AudioHandler, AudioCaptureGate
from lucy_voice.tts.mimic_tts import Mimic3TTS

logger = logging.getLogger(__name__)


class MouthWorker(BaseWorker):
    """Worker de TTS que reproduce respuestas del bus."""

    def __init__(
        self,
        worker_id: str,
        bus,
        config: LucyConfig,
        gate: Optional[AudioCaptureGate] = None,
    ):
        super().__init__(worker_id, bus)
        self.bus.subscribe("final_response", self.handle_message)
        self.config = config
        self.audio = AudioHandler(config)
        self.tts = Mimic3TTS(config)
        self.gate = gate
        self._lock = asyncio.Lock()

    async def handle_message(self, message: LucyMessage):
        if message.type == MessageType.EVENT and message.receiver == "final_response":
            text = message.content
            await self._speak(text, origin=message)
            return

        if message.type != MessageType.COMMAND:
            return

        if message.content == "speak":
            text = message.data.get("text") or message.content
            await self._speak(text, origin=message)
            return
        if message.content == "stop":
            await self.send_response(message, "Detener audio no implementado.")
            return

        await self.send_error(message, f"Comando desconocido: {message.content}")

    async def _speak(self, text: str, origin: LucyMessage) -> None:
        if not text:
            if origin.type == MessageType.COMMAND:
                await self.send_error(origin, "No recibí texto para hablar.")
            return

        async with self._lock:
            try:
                if self.gate:
                    self.gate.pause()
                audio_data, sr = await asyncio.to_thread(self.tts.synthesize, text)
                if audio_data is None:
                    raise RuntimeError("No pude sintetizar audio.")
                interrupted = await asyncio.to_thread(self.audio.play_audio, audio_data, sr)
                await self.send_event(
                    "broadcast",
                    "tts_done",
                    {"interrupted": interrupted, "chars": len(text)},
                )
                if origin.type == MessageType.COMMAND:
                    await self.send_response(origin, "TTS reproducido.", {"interrupted": interrupted})
            except Exception as exc:
                logger.warning("MouthWorker error: %s", exc)
                if origin.type == MessageType.COMMAND:
                    await self.send_error(origin, f"Error de TTS: {exc}")
            finally:
                if self.gate:
                    self.gate.resume()
