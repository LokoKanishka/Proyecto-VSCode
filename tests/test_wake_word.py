"""
Unit tests for wake word detection module.

Tests wake word functionality with mocked audio input.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import numpy as np
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lucy_tools.wake_word import WakeWordDetector, build_wakeword_model, wait_for_wake_word


class TestWakeWordDetector(unittest.TestCase):
    """Test WakeWordDetector class."""
    
    @patch('lucy_tools.wake_word.OpenWakeWordModel')
    def test_init_with_defaults(self, mock_model_class):
        """Test initialization with default models."""
        mock_instance = MagicMock()
        mock_model_class.return_value = mock_instance
        
        detector = WakeWordDetector()
        
        self.assertEqual(detector.threshold, 0.5)
        self.assertEqual(detector.model_paths, [])
        mock_model_class.assert_called_once_with()
    
    @patch('lucy_tools.wake_word.OpenWakeWordModel')
    def test_init_with_custom_model(self, mock_model_class):
        """Test initialization with custom model path."""
        mock_instance = MagicMock()
        mock_model_class.return_value = mock_instance
        
        model_paths = ["/path/to/model.onnx"]
        detector = WakeWordDetector(model_paths=model_paths, threshold=0.7)
        
        self.assertEqual(detector.threshold, 0.7)
        self.assertEqual(detector.model_paths, model_paths)
        mock_model_class.assert_called_once_with(wakeword_models=model_paths)
    
    @patch('lucy_tools.wake_word.OpenWakeWordModel')
    def test_predict(self, mock_model_class):
        """Test prediction on audio frame."""
        mock_model = MagicMock()
        mock_model.predict.return_value = {"hey_jarvis": 0.8, "alexa": 0.1}
        mock_model_class.return_value = mock_model
        
        detector = WakeWordDetector()
        
        # Test with bytes
        audio_frame = np.zeros(1280, dtype=np.int16).tobytes()
        result = detector.predict(audio_frame)
        
        self.assertIn("hey_jarvis", result)
        self.assertEqual(result["hey_jarvis"], 0.8)
        mock_model.predict.assert_called_once()
    
    @patch('lucy_tools.wake_word.OpenWakeWordModel')
    def test_is_detected_positive(self, mock_model_class):
        """Test detection when score exceeds threshold."""
        mock_model_class.return_value = MagicMock()
        
        detector = WakeWordDetector(threshold=0.5)
        predictions = {"hey_jarvis": 0.8, "alexa": 0.1}
        
        detected, model_name = detector.is_detected(predictions)
        
        self.assertTrue(detected)
        self.assertEqual(model_name, "hey_jarvis")
    
    @patch('lucy_tools.wake_word.OpenWakeWordModel')
    def test_is_detected_negative(self, mock_model_class):
        """Test no detection when all scores below threshold."""
        mock_model_class.return_value = MagicMock()
        
        detector = WakeWordDetector(threshold=0.5)
        predictions = {"hey_jarvis": 0.3, "alexa": 0.1}
        
        detected, model_name = detector.is_detected(predictions)
        
        self.assertFalse(detected)
        self.assertIsNone(model_name)


class TestBuildWakewordModel(unittest.TestCase):
    """Test build_wakeword_model function."""
    
    @patch('lucy_tools.wake_word.WakeWordDetector')
    def test_disabled_config(self, mock_detector_class):
        """Test that None is returned when wake word is disabled."""
        config = {"wake_word": {"enabled": False}}
        
        result = build_wakeword_model(config)
        
        self.assertIsNone(result)
        mock_detector_class.assert_not_called()
    
    @patch('lucy_tools.wake_word.WakeWordDetector')
    def test_enabled_with_defaults(self, mock_detector_class):
        """Test building with enabled but default settings."""
        mock_instance = MagicMock()
        mock_detector_class.return_value = mock_instance
        
        config = {
            "wake_word": {
                "enabled": True,
                "model_paths": [],
                "confidence_threshold": 0.6
            }
        }
        
        result = build_wakeword_model(config)
        
        self.assertIsNotNone(result)
        mock_detector_class.assert_called_once_with(model_paths=None, threshold=0.6)
    
    @patch('os.path.exists')
    @patch('lucy_tools.wake_word.WakeWordDetector')
    def test_enabled_with_valid_model_path(self, mock_detector_class, mock_exists):
        """Test building with valid custom model path."""
        mock_exists.return_value = True
        mock_instance = MagicMock()
        mock_detector_class.return_value = mock_instance
        
        model_path = "/valid/model.onnx"
        config = {
            "wake_word": {
                "enabled": True,
                "model_paths": [model_path],
                "confidence_threshold": 0.5
            }
        }
        
        result = build_wakeword_model(config)
        
        self.assertIsNotNone(result)
        mock_detector_class.assert_called_once_with(model_paths=[model_path], threshold=0.5)


class TestWaitForWakeWord(unittest.TestCase):
    """Test wait_for_wake_word function."""
    
    @patch('lucy_tools.wake_word.time.time')
    @patch('lucy_tools.wake_word.time.sleep')
    def test_detection_success(self, mock_sleep, mock_time):
        """Test successful wake word detection."""
        # Mock detector
        mock_detector = MagicMock()
        mock_detector.predict.return_value = {"hey_jarvis": 0.9}
        mock_detector.is_detected.return_value = (True, "hey_jarvis")
        mock_detector.threshold = 0.5
        
        # Mock audio callback (returns one frame)
        call_count = [0]
        def audio_callback():
            call_count[0] += 1
            return np.zeros(1280, dtype=np.int16).tobytes()
        
        # Mock time to avoid actual wait
        mock_time.return_value = 0.0
        
        result = wait_for_wake_word(
            detector=mock_detector,
            audio_callback=audio_callback,
            cooldown_seconds=0.1
        )
        
        self.assertTrue(result)
        self.assertGreater(call_count[0], 0)
    
    @patch('lucy_tools.wake_word.time.time')
    @patch('lucy_tools.wake_word.time.sleep')
    def test_timeout(self, mock_sleep, mock_time):
        """Test timeout when wake word not detected."""
        # Mock detector that never detects
        mock_detector = MagicMock()
        mock_detector.predict.return_value = {"hey_jarvis": 0.1}
        mock_detector.is_detected.return_value = (False, None)
        
        # Mock audio callback
        def audio_callback():
            return np.zeros(1280, dtype=np.int16).tobytes()
        
        # Mock time to simulate timeout
        time_sequence = [0.0, 0.5, 1.0, 1.5, 2.0, 2.6]  # Exceeds 2.5s max_wait
        mock_time.side_effect = time_sequence
        
        result = wait_for_wake_word(
            detector=mock_detector,
            audio_callback=audio_callback,
            max_wait_seconds=2.5
        )
        
        self.assertFalse(result)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
