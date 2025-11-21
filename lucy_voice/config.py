from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import yaml

@dataclass
class LucyConfig:
    # Paths
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    
    # Whisper
    whisper_model_name: str = "Systran/faster-whisper-small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    
    # Ollama
    ollama_model: str = "gpt-oss:20b"
    ollama_host: str = "http://localhost:11434"
    
    # TTS
    tts_voice: str = "en_US/ljspeech_low"
    
    # Audio / VAD
    sample_rate: int = 16000
    channels: int = 1
    dtype: str = "float32"
    record_seconds_fixed: float = 4.0
    vad_aggressiveness: int = 2
    vad_frame_duration_ms: int = 30
    silence_duration_stop: float = 1.0
    max_record_seconds: float = 10.0
    
    # Wake Word
    wakeword_model_paths: list[str] = field(default_factory=list)
    wakeword_threshold: float = 0.15
    wakeword_cooldown: float = 4.0

    @classmethod
    def load_from_yaml(cls, path: str | Path) -> LucyConfig:
        path = Path(path)
        if not path.exists():
            return cls()
            
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            
        # Filter keys that exist in the dataclass
        valid_keys = cls.__annotations__.keys()
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        
        # Handle paths specifically if needed, or rely on defaults
        config = cls(**filtered_data)
        
        # Resolve relative paths if necessary (e.g. for wakeword models)
        # For now, we assume paths in yaml are either absolute or relative to CWD.
        # We could make them relative to the config file location if we wanted.
        
        return config

    def save_to_yaml(self, path: str | Path) -> None:
        data = {k: getattr(self, k) for k in self.__annotations__.keys()}
        # Convert Path objects to strings for YAML
        if isinstance(data.get("base_dir"), Path):
            data["base_dir"] = str(data["base_dir"])
            
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
