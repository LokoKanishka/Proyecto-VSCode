import torch
from sam2.build_sam import build_sam2
from sam2.sam2_image_predictor import SAM2ImagePredictor
from PIL import Image
import numpy as np

class SAM2Adapter:
    def __init__(self, checkpoint_path="checkpoints/sam2_hiera_small.pt", model_cfg="sam2_hiera_s.yaml", device=None):
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device
            
        print(f"Loading SAM2 model from {checkpoint_path} to {self.device}...")
        self.sam2_model = build_sam2(model_cfg, checkpoint_path, device=self.device)
        self.predictor = SAM2ImagePredictor(self.sam2_model)

    def set_image(self, image_path_or_array):
        """
        Set the image for the predictor.
        image_path_or_array: can be a file path (str) or a numpy array (RGB).
        """
        if isinstance(image_path_or_array, str):
            image = Image.open(image_path_or_array)
            image = np.array(image.convert("RGB"))
        else:
            image = image_path_or_array
            
        self.predictor.set_image(image)

    def predict_box(self, box):
        """
        Predict mask from a bounding box.
        box: [x1, y1, x2, y2]
        """
        masks, scores, logits = self.predictor.predict(
            box=np.array(box),
            multimask_output=False
        )
        # Return the best mask
        return masks[0], scores[0]

    def predict_point(self, point_coords, point_labels):
        """
        Predict mask from points.
        point_coords: [[x, y], ...]
        point_labels: [1, 0, ...] (1 for foreground, 0 for background)
        """
        masks, scores, logits = self.predictor.predict(
            point_coords=np.array(point_coords),
            point_labels=np.array(point_labels),
            multimask_output=False
        )
        return masks[0], scores[0]
