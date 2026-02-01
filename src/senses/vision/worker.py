import ray
import os
import time
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from loguru import logger
from PIL import Image

# Import Adapters
from src.vision.sam2_adapter import SAM2Adapter
from ultralytics import YOLO

@ray.remote(num_gpus=0.3)  # Reserve fractional GPU
class VisionActor:
    """
    Persistent Ray Actor for Vision Tasks.
    Holds heavy models (SAM2, YOLO) in VRAM to avoid reload latency.
    """
    def __init__(self):
        self.start_time = time.time()
        logger.info("👁️ VisionActor initializing...")
        
        # Load YOLOv8 (for UI Detection)
        # Using a small standard model for now as 'rico' weights might not be present.
        # Ideally this would be 'yolov8n.pt' or a custom trained one.
        try:
            self.yolo_model = YOLO("yolov8n.pt") 
            logger.info("✅ YOLOv8 loaded successfully.")
        except Exception as e:
            logger.error(f"❌ Failed to load YOLOv8: {e}")
            self.yolo_model = None

        # Load SAM2 (for Segmentation)
        try:
            # Assumes checkpoints are downloaded in /checkpoints
            ckpt_path = os.path.join(os.getcwd(), "checkpoints", "sam2_hiera_small.pt")
            if os.path.exists(ckpt_path):
                self.sam2 = SAM2Adapter(checkpoint_path=ckpt_path)
                logger.info("✅ SAM2 loaded successfully.")
            else:
                logger.warning(f"⚠️ SAM2 checkpoint not found at {ckpt_path}. SAM2 disabled.")
                self.sam2 = None
        except Exception as e:
            logger.error(f"❌ Failed to load SAM2: {e}")
            self.sam2 = None

    async def ping(self) -> str:
        return "pong"

    async def detect_ui(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Detect UI elements in the given image using YOLO.
        Returns a list of detected objects with bounding boxes.
        """
        if not self.yolo_model:
            return {"error": "YOLO model not loaded"}
        
        try:
            results = self.yolo_model(image_path)
            detections = []
            for r in results:
                for box in r.boxes:
                    b = box.xyxy[0].tolist() # [x1, y1, x2, y2]
                    conf = float(box.conf)
                    cls = int(box.cls)
                    label = self.yolo_model.names[cls]
                    detections.append({
                        "label": label,
                        "confidence": conf,
                        "box": [int(x) for x in b]
                    })
            return detections
        except Exception as e:
            logger.error(f"Error in detect_ui: {e}")
            return {"error": str(e)}

    async def segment_point(self, image_path: str, x: int, y: int) -> Dict[str, Any]:
        """
        Segment object at (x,y) using SAM2.
        """
        if not self.sam2:
            return {"error": "SAM2 model not loaded"}
        
        try:
            self.sam2.set_image(image_path)
            mask, score = self.sam2.predict_point([[x, y]], [1])
            # mask is a boolean array, we might want to return bounding box or RLE
            # For now, let's return the bounding box of the mask
            rows = np.any(mask, axis=1)
            cols = np.any(mask, axis=0)
            if not np.any(rows) or not np.any(cols):
                return {"error": "No object found at point"}
                
            ymin, ymax = np.where(rows)[0][[0, -1]]
            xmin, xmax = np.where(cols)[0][[0, -1]]
            
            return {
                "score": float(score),
                "box": [int(xmin), int(ymin), int(xmax), int(ymax)]
            }
        except Exception as e:
            logger.error(f"Error in segment_point: {e}")
            return {"error": str(e)}
