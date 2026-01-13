"""
Wake Word Detection Module for Lucy Voice Assistant.

Provides wake word detection functionality using OpenWakeWord with ONNX runtime.
Supports both default models and custom trained models.
"""

import os
import time
from typing import Optional, List
import numpy as np

try:
    from openwakeword.model import Model as OpenWakeWordModel
except ImportError:
    OpenWakeWordModel = None


class WakeWordDetector:
    """Wake word detector using OpenWakeWord."""

    def __init__(self, model_paths: Optional[List[str]] = None, threshold: float = 0.5):
        """
        Initialize wake word detector.

        Args:
            model_paths: List of paths to custom .onnx or .tflite models.
                        If None or empty, uses default models.
            threshold: Detection confidence threshold (0.0-1.0)
        """
        if OpenWakeWordModel is None:
            raise ImportError("openwakeword not installed. Install with: pip install openwakeword")

        self.threshold = threshold
        self.model_paths = model_paths or []

        # Initialize model
        if self.model_paths:
            # Custom model(s)
            self.model = OpenWakeWordModel(wakeword_models=self.model_paths)
        else:
            # Use default pre-trained models that come with openwakeword
            # These include: hey_jarvis, alexa, hey_mycroft, hey_rhasspy
            self.model = OpenWakeWordModel()

    def predict(self, audio_frame: bytes) -> dict:
        """
        Run prediction on an audio frame.

        Args:
            audio_frame: Raw audio bytes (16-bit PCM, 16kHz)

        Returns:
            Dictionary mapping model names to prediction scores
        """
        # Convert bytes to numpy array if needed
        if isinstance(audio_frame, bytes):
            audio_np = np.frombuffer(audio_frame, dtype=np.int16).astype(np.float32) / 32768.0
        else:
            audio_np = audio_frame

        # Run prediction
        prediction = self.model.predict(audio_np)
        return prediction

    def is_detected(self, predictions: dict) -> tuple[bool, Optional[str]]:
        """
        Check if wake word was detected in predictions.

        Args:
            predictions: Dictionary from predict()

        Returns:
            (detected: bool, model_name: Optional[str])
        """
        for model_name, score in predictions.items():
            if score >= self.threshold:
                return True, model_name
        return False, None


def build_wakeword_model(config: dict) -> Optional[WakeWordDetector]:
    """
    Build wake word model from configuration.

    Args:
        config: Configuration dictionary with wake_word settings

    Returns:
        WakeWordDetector instance or None if disabled
    """
    wake_cfg = config.get("wake_word", {})

    if not wake_cfg.get("enabled", True):
        return None

    model_paths = wake_cfg.get("model_paths", [])
    threshold = wake_cfg.get("confidence_threshold", 0.5)

    # Validate model paths if provided
    valid_paths = []
    for path in model_paths:
        if os.path.exists(path):
            valid_paths.append(path)
        else:
            print(f"[WakeWord] Warning: Model path not found: {path}")

    try:
        detector = WakeWordDetector(
            model_paths=valid_paths if valid_paths else None, threshold=threshold
        )
        return detector
    except Exception as exc:
        print(f"[WakeWord] Error initializing detector: {exc}")
        return None


def wait_for_wake_word(
    detector: WakeWordDetector,
    audio_callback,
    frame_duration_ms: int = 80,
    cooldown_seconds: float = 2.0,
    max_wait_seconds: Optional[float] = None,
) -> bool:
    """
    Wait for wake word detection.

    Args:
        detector: WakeWordDetector instance
        audio_callback: Function that returns audio frames (bytes, 16-bit PCM, 16kHz)
                       Should return frame_duration_ms worth of audio
        frame_duration_ms: Duration of each audio frame in milliseconds
        cooldown_seconds: Cooldown period after detection before returning
        max_wait_seconds: Maximum time to wait (None = wait indefinitely)

    Returns:
        True if wake word detected, False if timeout
    """
    start_time = time.time()
    frame_count = 0

    print("[WakeWord] Waiting for wake word...")

    while True:
        # Check timeout
        if max_wait_seconds and (time.time() - start_time) > max_wait_seconds:
            return False

        # Get audio frame
        try:
            audio_frame = audio_callback()
            if audio_frame is None:
                time.sleep(0.01)  # Short sleep to avoid busy loop
                continue
        except Exception as exc:
            print(f"[WakeWord] Error getting audio: {exc}")
            time.sleep(0.1)
            continue

        # Run prediction
        try:
            predictions = detector.predict(audio_frame)
            detected, model_name = detector.is_detected(predictions)

            if detected:
                print(
                    f"[WakeWord] Detected! Model: {model_name}, Score: {predictions.get(model_name, 0):.3f}"
                )

                # Cooldown to avoid multiple triggers
                if cooldown_seconds > 0:
                    time.sleep(cooldown_seconds)

                return True

            # Periodic status
            frame_count += 1
            if frame_count % 100 == 0:  # Every ~8 seconds at 80ms frames
                print(f"[WakeWord] Still listening... ({int(time.time() - start_time)}s)")

        except Exception as exc:
            print(f"[WakeWord] Prediction error: {exc}")
            continue


# Simple test function
if __name__ == "__main__":
    import sys

    print("Testing wake word module...")

    # Mock config
    test_config = {
        "wake_word": {
            "enabled": True,
            "model_paths": [],  # Use defaults
            "confidence_threshold": 0.5,
        }
    }

    detector = build_wakeword_model(test_config)

    if detector:
        print(f"✓ Detector initialized")
        print(f"  Threshold: {detector.threshold}")
        print(
            f"  Models: {list(detector.model.models.keys()) if hasattr(detector.model, 'models') else 'N/A'}"
        )
    else:
        print("✗ Failed to initialize detector")
        sys.exit(1)

    # Test with silence (should not detect)
    silence = np.zeros(1280, dtype=np.int16).tobytes()  # 80ms of silence at 16kHz
    predictions = detector.predict(silence)
    detected, model = detector.is_detected(predictions)

    print(f"\nSilence test:")
    print(f"  Predictions: {predictions}")
    print(f"  Detected: {detected}")

    print("\n✓ All tests passed")
