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
from src.vision.vision_pipeline import VisionPipeline

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

        # Labels A1..H10
        for r in range(self.grid_rows):
            for c in range(self.grid_cols):
                label = f"{chr(ord('A') + c)}{r + 1}"
                x = int(c * dx + 4)
                y = int(r * dy + 18)
                cv2.putText(img_bgr, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
                cv2.putText(img_bgr, label, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        _, buffer = cv2.imencode('.jpg', img_bgr)
        img_base64 = base64.b64encode(buffer).decode('utf-8')
        return img_base64, {"width": w, "height": h, "cell_w": dx, "cell_h": dy}

class VisionWorker(BaseWorker):
    """Agente que 've' la pantalla, describe y devuelve coordenadas confiables."""

    def __init__(self, worker_id, bus):
        super().__init__(worker_id, bus)
        self.eye = ScreenEye()
        self.model = "llava"
        self.pipeline = VisionPipeline()

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return
        command = message.content
        logger.info(f"👁️ VisionWorker recibió comando: {command}")
        if command == "analyze_screen":
            prompt = message.data.get("prompt", "Describe qué ves en la pantalla.")
            await self.analyze_screen(message, prompt)
        elif command == "analyze_image":
            prompt = message.data.get("prompt", "Describe qué ves en la imagen.")
            await self.analyze_image(message, prompt)
        else:
            await self.send_error(message, f"Comando desconocido: {command}")

    async def analyze_screen(self, original_msg: LucyMessage, prompt: str):
        logger.info("📸 Capturando pantalla...")
        img_b64, meta = self.eye.capture_with_grid()

        description = "No pude procesar la imagen."
        grid_hint = "E5"
        extra: Dict[str, Any] = {"meta": meta}
        use_advanced = bool(original_msg.data.get("advanced", False))

        try:
            if not HAS_VISION_LIBS:
                raise RuntimeError("Faltan librerías de visión (mss/cv2).")
            if use_advanced:
                img_bytes = base64.b64decode(img_b64)
                img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
                frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
                analysis = self.pipeline.analyze(frame, advanced=True)
                extra["ui_elements"] = [
                    {"bbox": el.bbox, "text": el.text, "type": el.element_type, "confidence": el.confidence}
                    for el in analysis.get("elements", [])
                ]
                extra["ocr_count"] = analysis.get("ocr_count")
                extra["detector_count"] = analysis.get("detector_count")
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

    async def analyze_image(self, original_msg: LucyMessage, prompt: str):
        img_b64 = original_msg.data.get("image_b64")
        if not img_b64:
            await self.send_error(original_msg, "Falta image_b64 para analizar.")
            return
        description = "No pude procesar la imagen."
        grid_hint = "E5"
        extra: Dict[str, Any] = {"source": original_msg.data.get("source", "external_image")}

        try:
            if not HAS_VISION_LIBS:
                raise RuntimeError("Faltan librerías de visión (mss/cv2).")
            img_bytes = base64.b64decode(img_b64)
            img_arr = np.frombuffer(img_bytes, dtype=np.uint8)
            frame = cv2.imdecode(img_arr, cv2.IMREAD_COLOR)
            if frame is None:
                raise RuntimeError("No pude decodificar la imagen.")
            if original_msg.data.get("advanced"):
                analysis = self.pipeline.analyze(frame)
                extra["ui_elements"] = [
                    {"bbox": el.bbox, "text": el.text, "type": el.element_type, "confidence": el.confidence}
                    for el in analysis.get("elements", [])
                ]
                extra["ocr_count"] = analysis.get("ocr_count")
                extra["detector_count"] = analysis.get("detector_count")

            # Overlay grid for grounding
            grid_img = self._overlay_grid(frame.copy())
            _, buffer = cv2.imencode(".jpg", grid_img)
            grid_b64 = base64.b64encode(buffer).decode("utf-8")

            response = ollama.chat(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": prompt,
                    "images": [grid_b64],
                }]
            )
            description = response["message"]["content"]
            grid_hint = self._find_grid_hint(description)
        except Exception as exc:
            logger.warning("VisionWorker analyze_image fallback: %s", exc)
            description = f"Modo degradado: {exc}"

        await self.send_response(
            original_msg,
            description,
            {"grid_hint": grid_hint, **extra}
        )

    def _overlay_grid(self, img):
        h, w, _ = img.shape
        dy, dx = h / self.eye.grid_rows, w / self.eye.grid_cols
        color = (0, 255, 0)
        for i in range(1, self.eye.grid_rows):
            y = int(dy * i)
            cv2.line(img, (0, y), (w, y), color, 1)
        for j in range(1, self.eye.grid_cols):
            x = int(dx * j)
            cv2.line(img, (x, 0), (x, h), color, 1)
        return img

    @staticmethod
    def _find_grid_hint(text: str) -> str:
        import re

        pattern = re.compile(r"\b([A-H](?:10|[1-9]))\b")
        match = pattern.search(text.upper())
        return match.group(1) if match else "E5"

    def _fallback_grid_code(self, prompt: str) -> str:
        code = self._find_grid_hint(prompt)
        return code if code else "E5"
