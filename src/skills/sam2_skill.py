import json
import os
from src.skills.base_skill import BaseSkill
from src.vision.sam2_adapter import SAM2Adapter

class SAM2SegmentationSkill(BaseSkill):
    def __init__(self, adapter: SAM2Adapter = None):
        self._adapter = adapter or SAM2Adapter()

    @property
    def name(self) -> str:
        return "segment_object"

    @property
    def description(self) -> str:
        return "Segmenta un objeto basado en un punto o caja para obtener precision visual avanzada."

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "box": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[x1, y1, x2, y2]"
                },
                "point": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "[x, y]"
                }
            }
        }

    def execute(self, box=None, point=None) -> str:
        # This would usually use the last captured image
        last_img = "/tmp/lucy_vision.jpg" 
        if not os.path.exists(last_img):
            return "No hay captura previa para segmentar."
            
        self._adapter.set_image(last_img)
        if box:
            mask, score = self._adapter.predict_box(box)
        elif point:
            mask, score = self._adapter.predict_point([point], [1])
        else:
            return "Se requiere box o point."
            
        return json.dumps({"status": "success", "score": float(score)})
