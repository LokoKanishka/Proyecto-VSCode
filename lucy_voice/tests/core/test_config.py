import unittest
import tempfile
import os
from pathlib import Path
from lucy_voice.config import LucyConfig

class TestLucyConfig(unittest.TestCase):
    def test_defaults(self):
        config = LucyConfig()
        self.assertEqual(config.sample_rate, 16000)
        self.assertEqual(config.whisper_device, "cpu")

    def test_load_from_yaml(self):
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp.write("sample_rate: 44100\nwhisper_device: cuda")
            tmp_path = tmp.name
        
        try:
            config = LucyConfig.load_from_yaml(tmp_path)
            self.assertEqual(config.sample_rate, 44100)
            self.assertEqual(config.whisper_device, "cuda")
            # Check default remains
            self.assertEqual(config.whisper_compute_type, "int8")
        finally:
            os.remove(tmp_path)

    def test_save_to_yaml(self):
        config = LucyConfig(sample_rate=48000)
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tmp:
            tmp_path = tmp.name
            
        try:
            config.save_to_yaml(tmp_path)
            loaded = LucyConfig.load_from_yaml(tmp_path)
            self.assertEqual(loaded.sample_rate, 48000)
        finally:
            os.remove(tmp_path)
