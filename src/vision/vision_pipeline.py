from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import os

from src.vision.rico_dataset import load_rico_annotations

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

try:
    from segment_anything import sam_model_registry, SamPredictor  # type: ignore
    HAS_SAM = True
except Exception:
    HAS_SAM = False

logger = logging.getLogger(__name__)


@dataclass
class UIElement:
    bbox: Tuple[int, int, int, int]
    text: Optional[str] = None
    element_type: Optional[str] = None
    confidence: float = 0.0


class VisionPipeline:
    """Pipeline de visión: preprocesado, OCR y detección de UI."""

    def __init__(
        self,
        yolo_model_path: Optional[str] = None,
        sam_checkpoint: Optional[str] = None,
        sam_model_type: str = "vit_h",
    ):
        self.yolo_model_path = yolo_model_path
        self._yolo = None
        if HAS_YOLO and yolo_model_path:
            try:
                self._yolo = YOLO(yolo_model_path)
            except Exception as exc:
                logger.warning("No pude cargar YOLO: %s", exc)
        self._sam = None
        self._sam_predictor = None
        if HAS_SAM and sam_checkpoint:
            try:
                sam = sam_model_registry[sam_model_type](checkpoint=sam_checkpoint)
                self._sam_predictor = SamPredictor(sam)
                self._sam = sam
            except Exception as exc:
                logger.warning("No pude cargar SAM: %s", exc)
        self._sam_cache: Dict[str, Dict[str, Any]] = {}
        self._sam_cache_order: List[str] = []
        self._sam_cache_size = int(os.getenv("LUCY_SAM_CACHE_SIZE", "32"))
        self._ocr_cache: Dict[str, List[UIElement]] = {}
        self._ocr_cache_order: List[str] = []
        self._ocr_cache_size = int(os.getenv("LUCY_OCR_CACHE_SIZE", "32"))
        rico_path = os.getenv("LUCY_RICO_PATH")
        self.rico_samples = load_rico_annotations(rico_path, limit=200) if rico_path else []

    def preprocess(self, image: Any) -> Any:
        if not HAS_CV:
            return image
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel)
        closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, kernel)
        return closed

    def morphology_features(self, image: Any) -> Dict[str, Any]:
        if not HAS_CV:
            return {}
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        top_hat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, kernel)
        black_hat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT, kernel)
        gradient = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, kernel)
        skeleton = self._skeletonize(binary)
        skeleton_density = float(skeleton.mean() / 255.0) if skeleton is not None else 0.0
        return {
            "top_hat_mean": float(top_hat.mean()),
            "black_hat_mean": float(black_hat.mean()),
            "gradient_mean": float(gradient.mean()),
            "binary_density": float(binary.mean() / 255.0),
            "skeleton_density": skeleton_density,
        }

    def run_ocr(self, image: Any, lang: str = "spa+eng") -> List[UIElement]:
        if not HAS_TESS:
            return []
        cache_key = None
        try:
            cache_key = str(hash(image.tobytes()))
        except Exception:
            cache_key = None
        if cache_key and cache_key in self._ocr_cache:
            return self._ocr_cache[cache_key]
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
        if cache_key:
            self._ocr_cache[cache_key] = elements
            self._ocr_cache_order.append(cache_key)
            if len(self._ocr_cache_order) > self._ocr_cache_size:
                old = self._ocr_cache_order.pop(0)
                self._ocr_cache.pop(old, None)
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

    def analyze(self, image: Any, lang: str = "spa+eng", advanced: bool = False) -> Dict[str, Any]:
        processed = self.preprocess(image) if HAS_CV else image
        ocr_elements = self.run_ocr(processed, lang=lang)
        detector_elements = self.run_detector(image)
        elements = ocr_elements + detector_elements
        payload = {
            "elements": elements,
            "ocr_count": len(ocr_elements),
            "detector_count": len(detector_elements),
        }
        if advanced:
            payload["morphology"] = self.morphology_features(image)
            payload["som"] = self.build_semantic_map(elements, image=image)
        return payload

    def build_semantic_map(self, elements: List[UIElement], image: Any = None) -> Dict[str, Any]:
        """Construye un mapa semántico simple con etiquetas y ids."""
        som_elements: List[Dict[str, Any]] = []
        for idx, el in enumerate(elements):
            label = el.text.strip() if el.text else (el.element_type or "element")
            norm_label = label.lower().strip()
            bbox = el.bbox
            w = bbox[2]
            h = bbox[3]
            shape = "wide" if w > h * 2 else ("tall" if h > w * 2 else "squareish")
            area = w * h
            size = "small"
            if area > 40000:
                size = "large"
            elif area > 10000:
                size = "medium"
            color = None
            if HAS_CV and image is not None:
                try:
                    x, y, w_, h_ = bbox
                    crop = image[y : y + h_, x : x + w_]
                    if crop is not None and crop.size:
                        mean = crop.mean(axis=(0, 1))
                        color = [int(mean[2]), int(mean[1]), int(mean[0])]
                except Exception:
                    color = None
            som_elements.append(
                {
                    "id": f"el_{idx:03d}",
                    "label": label,
                    "label_norm": norm_label,
                    "bbox": bbox,
                    "type": el.element_type,
                    "confidence": el.confidence,
                    "shape": shape,
                    "size": size,
                    "color_rgb": color,
                    "source": "ocr" if el.text else "detector",
                }
            )
        return {
            "count": len(som_elements),
            "elements": som_elements,
        }

    def segment_with_sam(self, image: Any, bbox: Tuple[int, int, int, int]) -> Optional[Dict[str, Any]]:
        """Refina un bbox usando SAM (si está disponible)."""
        if not (HAS_SAM and self._sam_predictor):
            return None
        import numpy as np
        key = f"{bbox}"
        if key in self._sam_cache:
            return self._sam_cache[key]
        x, y, w, h = bbox
        x1, y1, x2, y2 = x, y, x + w, y + h
        try:
            self._sam_predictor.set_image(image)
            masks, scores, _ = self._sam_predictor.predict(
                box=np.array([x1, y1, x2, y2]),
                multimask_output=True,
            )
            if masks is None or len(masks) == 0:
                return None
            best_idx = int(np.argmax(scores))
            result = {
                "mask": masks[best_idx],
                "score": float(scores[best_idx]),
            }
            self._sam_cache[key] = result
            self._sam_cache_order.append(key)
            if len(self._sam_cache_order) > self._sam_cache_size:
                old = self._sam_cache_order.pop(0)
                self._sam_cache.pop(old, None)
            return result
        except Exception as exc:
            logger.warning("SAM segment falló: %s", exc)
            return None

    def _skeletonize(self, binary: Any):
        if not HAS_CV:
            return None
        img = binary.copy()
        img = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY)[1]
        skeleton = cv2.zeros(img.shape, dtype=img.dtype)
        element = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
        while True:
            eroded = cv2.erode(img, element)
            temp = cv2.dilate(eroded, element)
            temp = cv2.subtract(img, temp)
            skeleton = cv2.bitwise_or(skeleton, temp)
            img = eroded.copy()
            if cv2.countNonZero(img) == 0:
                break
        return skeleton
