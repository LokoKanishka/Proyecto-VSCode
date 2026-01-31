import logging
import base64
import io
import time
import json
from typing import Tuple, Dict, Any

try:
    import mss
    import cv2
    import numpy as np
    import ollama
    HAS_VISION_LIBS = True
except ImportError:
    HAS_VISION_LIBS = False

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)

class ScreenEye:
    """
    Motor de captura y procesamiento visual.
    Implementa 'Visión Asistida por Grilla'.
    """
    def __init__(self):
        if HAS_VISION_LIBS:
            self.sct = mss.mss()
        self.grid_rows = 10
        self.grid_cols = 10

    def capture_with_grid(self, monitor_idx=1) -> Tuple[str, Dict]:
        if not HAS_VISION_LIBS:
            return "", {"error": "Faltan librerías (mss, cv2)"}

        monitor = self.sct.monitors[monitor_idx] if len(self.sct.monitors) > monitor_idx else self.sct.monitors[0]
        img = np.array(self.sct.grab(monitor))
        img_bgr = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        h, w, _ = img_bgr.shape
        dy, dx = h / self.grid_rows, w / self.grid_cols
        color = (0, 255, 0)

        for i in range(1, self.grid_rows):
            y = int(dy * i)
            cv2.line(img_bgr, (0, y), (w, y), color, 1)
        for j in range(1, self.grid_cols):
            x = int(dx * j)
            cv2.line(img_bgr, (x, 0), (x, h), color, 1)

        _, buffer = cv2.imencode('.jpg', img_bgr)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return img_base64, {"width": w, "height": h, "cell_w": dx, "cell_h": dy}

class VisionWorker(BaseWorker):
    """Agente que 've' la pantalla, describe y devuelve coordenadas confiables."""

    def __init__(self, worker_id, bus):
        super().__init__(worker_id, bus)
        self.eye = ScreenEye()
        self.model = "llava"

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return
        command = message.content
        logger.info(f"👁️ VisionWorker recibió comando: {command}")
        if command == "analyze_screen":
            prompt = message.data.get("prompt", "Describe qué ves en la pantalla.")
            await self.analyze_screen(message, prompt)
        else:
            await self.send_error(message, f"Comando desconocido: {command}")

    async def analyze_screen(self, original_msg: LucyMessage, prompt: str):
        logger.info("📸 Capturando pantalla...")
        img_b64, meta = self.eye.capture_with_grid()

        description = "No pude procesar la imagen."
        grid_hint = "E5"
        extra: Dict[str, Any] = {"meta": meta}

        try:
            if not HAS_VISION_LIBS:
                raise RuntimeError("Faltan librerías de visión (mss/cv2).")
            logger.info(f"🧠 Consultando a {self.model}...")
            response = ollama.chat(
                model=self.model,
                messages=[{
                    'role': 'user',
                    'content': prompt,
                    'images': [img_b64]
                }]
            )
            description = response['message']['content']
            grid_hint = self._find_grid_hint(description)
            extra["model_response"] = response['message']
        except Exception as exc:
            logger.warning("VisionWorker fallback: %s", exc)
            grid_hint = self._fallback_grid_code(prompt)
            description = f"Modo degradado: {exc}"

        await self.send_response(
            original_msg,
            description,
            {"meta": meta, "grid_hint": grid_hint, **extra}
        )

    @staticmethod
    def _find_grid_hint(text: str) -> str:
        import re

        pattern = re.compile(r"\b([A-H](?:10|[1-9]))\b")
        match = pattern.search(text.upper())
        return match.group(1) if match else "E5"

    def _fallback_grid_code(self, prompt: str) -> str:
        code = self._find_grid_hint(prompt)
        return code if code else "E5"
