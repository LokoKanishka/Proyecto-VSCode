import asyncio
import logging
from typing import Optional

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType
from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.audio import AudioHandler, AudioCaptureGate
from lucy_voice.asr.fast_whisper_wrapper import WhisperASR

logger = logging.getLogger(__name__)


class EarWorker(BaseWorker):
    """Worker de escucha continua (micro + ASR) que publica eventos user_input."""

    def __init__(
        self,
        worker_id: str,
        bus,
        config: LucyConfig,
        gate: Optional[AudioCaptureGate] = None,
    ):
        super().__init__(worker_id, bus)
        self.config = config
        self.audio = AudioHandler(config)
        self.asr = WhisperASR(config)
        self.gate = gate
        self._running = False
        self._paused = False

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        cmd = message.content
        if cmd == "pause_listen":
            self._paused = True
            await self.send_response(message, "Escucha pausada.")
            return
        if cmd == "resume_listen":
            self._paused = False
            await self.send_response(message, "Escucha reanudada.")
            return
        if cmd == "listen_once":
            text = await self._listen_once()
            await self.send_response(message, text or "No detecté voz.")
            return
        if cmd == "stop":
            self.stop()
            await self.send_response(message, "Escucha detenida.")
            return

        await self.send_error(message, f"Comando desconocido: {cmd}")

    async def run(self) -> None:
        """Bucle de escucha continua; publica mensajes a user_input."""
        self._running = True
        logger.info("🎧 EarWorker activo (escucha continua).")
        while self._running:
            if self._paused:
                await asyncio.sleep(0.2)
                continue
            if self.gate and self.gate.is_paused():
                await self.gate.wait_for_resume()
            try:
                text = await self._listen_once()
            except Exception as exc:
                logger.warning("EarWorker error en escucha: %s", exc)
                await asyncio.sleep(0.5)
                continue

            if text:
                msg = LucyMessage(
                    sender=self.worker_id,
                    receiver="user_input",
                    type=MessageType.EVENT,
                    content=text,
                    data={"source": "mic"},
                )
                await self.bus.publish(msg)
            else:
                await asyncio.sleep(0.05)

    def stop(self) -> None:
        self._running = False

    async def _listen_once(self) -> str:
        audio = await asyncio.to_thread(
            self.audio.record_until_silence,
            self.config.max_record_seconds,
            self.config.silence_duration_stop,
        )
        if audio is None or len(audio) == 0:
            return ""
        text, _lang = await asyncio.to_thread(self.asr.transcribe, audio)
        return (text or "").strip()
