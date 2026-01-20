import json
import os

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "model": "Llama 3",
    "temperature": 0.7,
    "max_tokens": 2048,
    "system_prompt": "You are Lucy, a helpful AI assistant."
}

class SettingsManager:
    @staticmethod
    def load_settings() -> dict:
        if not os.path.exists(SETTINGS_FILE):
            return DEFAULT_SETTINGS.copy()
        
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                # Merge with defaults to ensure all keys exist
                settings = DEFAULT_SETTINGS.copy()
                settings.update(data)
                return settings
        except Exception as e:
            print(f"Error loading settings: {e}")
            return DEFAULT_SETTINGS.copy()

    @staticmethod
    def save_settings(settings: dict):
        try:
            with open(SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")
