import pytest

try:
    import numpy as np
    import cv2
except Exception:
    np = None
    cv2 = None

from src.vision.vision_pipeline import VisionPipeline


def test_morphology_features_skeleton_density():
    if np is None or cv2 is None:
        pytest.skip("opencv/numpy no disponible")
    img = np.zeros((100, 100, 3), dtype=np.uint8)
    cv2.line(img, (10, 50), (90, 50), (255, 255, 255), 2)
    pipeline = VisionPipeline()
    features = pipeline.morphology_features(img)
    assert features["skeleton_density"] > 0.0
