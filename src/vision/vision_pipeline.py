from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import cv2
    import numpy as np
    HAS_CV = True
except ImportError:
    HAS_CV = False

try:
    import pytesseract
    HAS_TESS = True
except ImportError:
    HAS_TESS = False

try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    bbox: Tuple[int, int, int, int]
    text: Optional[str] = None
    element_type: Optional[str] = None
    confidence: float = 0.0


class VisionPipeline:
    """Pipeline de visión: preprocesado, OCR y detección de UI."""

    def __init__(self, yolo_model_path: Optional[str] = None):
        self.yolo_model_path = yolo_model_path
        self._yolo = None
        if HAS_YOLO and yolo_model_path:
            try:
                self._yolo = YOLO(yolo_model_path)
            except Exception as exc:
                logger.warning("No pude cargar YOLO: %s", exc)

    def preprocess(self, image: Any) -> Any:
        if not HAS_CV:
            return image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        return closed

    def run_ocr(self, image: Any, lang: str = "spa+eng") -> List[UIElement]:
        if not HAS_TESS:
            return []
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        elements: List[UIElement] = []
        for i, text in enumerate(data.get("text", [])):
            if not text.strip():
                continue
            x = data["left"][i]
            y = data["top"][i]
            w = data["width"][i]
            h = data["height"][i]
            conf = float(data["conf"][i]) if data.get("conf") else 0.0
            elements.append(UIElement(bbox=(x, y, w, h), text=text, element_type="text", confidence=conf))
        return elements

    def run_detector(self, image: Any) -> List[UIElement]:
        if not (HAS_YOLO and self._yolo):
            return []
        results = self._yolo(image)
        elements: List[UIElement] = []
        for res in results:
            if not hasattr(res, "boxes"):
                continue
            for box in res.boxes:
                xyxy = box.xyxy[0].tolist()
                x1, y1, x2, y2 = map(int, xyxy)
                conf = float(box.conf[0]) if hasattr(box, "conf") else 0.0
                cls_name = None
                if hasattr(res, "names") and hasattr(box, "cls"):
                    cls_name = res.names.get(int(box.cls[0]))
                elements.append(UIElement(bbox=(x1, y1, x2 - x1, y2 - y1), element_type=cls_name, confidence=conf))
        return elements

    def analyze(self, image: Any, lang: str = "spa+eng") -> Dict[str, Any]:
        processed = self.preprocess(image) if HAS_CV else image
        ocr_elements = self.run_ocr(processed, lang=lang)
        detector_elements = self.run_detector(image)
        elements = ocr_elements + detector_elements
        return {
            "elements": elements,
            "ocr_count": len(ocr_elements),
            "detector_count": len(detector_elements),
        }
