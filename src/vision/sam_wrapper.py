import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from segment_anything import sam_model_registry, SamPredictor  # type: ignore
    HAS_SAM = True
except Exception:
    HAS_SAM = False


class SAMWrapper:
    """Wrapper liviano para Segment Anything (si está instalado)."""

    def __init__(self, model_type: str = "vit_b", checkpoint_path: Optional[str] = None):
        self.model_type = model_type
        self.checkpoint_path = checkpoint_path
        self.predictor = None
        if HAS_SAM and checkpoint_path:
            try:
                model = sam_model_registry[model_type](checkpoint=checkpoint_path)
                self.predictor = SamPredictor(model)
            except Exception as exc:
                logger.warning("No pude inicializar SAM: %s", exc)

    def segment(self, image: Any, point: Optional[tuple] = None, box: Optional[tuple] = None) -> Dict:
        if not self.predictor:
            return {"error": "SAM no disponible"}
        self.predictor.set_image(image)
        if box:
            masks, scores, _ = self.predictor.predict(box=box, multimask_output=True)
        elif point:
            masks, scores, _ = self.predictor.predict(point_coords=[point], point_labels=[1], multimask_output=True)
        else:
            return {"error": "Se requiere point o box"}
        best = int(scores.argmax())
        return {"mask": masks[best], "score": float(scores[best])}
