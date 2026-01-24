import os
from typing import Any, Dict, Optional

import requests
from loguru import logger

try:
    import yaml  # type: ignore
except Exception:
    yaml = None


class SwarmManager:
    def __init__(
        self,
        host: Optional[str] = None,
        main_model: Optional[str] = None,
        vision_model: Optional[str] = None,
        config_path: str = "config.yaml",
        timeout_s: float = 8.0,
    ):
        self._config = self._load_config(config_path)
        self.host = (
            host
            or os.getenv("LUCY_OLLAMA_HOST")
            or self._config.get("ollama_host")
            or "http://localhost:11434"
        )
        self.main_model = (
            main_model
            or os.getenv("LUCY_MAIN_MODEL")
            or os.getenv("LUCY_OLLAMA_MODEL")
            or self._config.get("ollama_model")
            or "llama3.1:8b"
        )
        self.vision_model = (
            vision_model
            or os.getenv("LUCY_VISION_MODEL")
            or self._config.get("ollama_vision_model")
            or "llava:latest"
        )
        swarm_cfg = self._config.get("swarm", {}) if isinstance(self._config.get("swarm"), dict) else {}
        self.persistent = self._parse_bool(
            os.getenv("LUCY_SWARM_PERSIST"),
            swarm_cfg.get("persistent_models", True),
        )
        self.keep_alive = self._parse_int(
            os.getenv("LUCY_SWARM_KEEP_ALIVE"),
            swarm_cfg.get("keep_alive", -1),
        )
        self.timeout_s = timeout_s
        self._active_profile: Optional[str] = None

        logger.info(
            "🧠 SwarmManager listo (host={}, main={}, vision={}, persistente={})",
            self.host,
            self.main_model,
            self.vision_model,
            self.persistent,
        )

    def set_profile(self, profile_name: str) -> None:
        if profile_name == self._active_profile:
            return
        if profile_name not in {"general", "vision"}:
            logger.warning("Perfil desconocido: {}", profile_name)
            return

        logger.info("🔀 Swarm: cambiando a perfil '{}'", profile_name)
        if profile_name == "general":
            self._touch_model(self.main_model, keep_alive=self.keep_alive, label="main")
            if self.vision_model and self.vision_model != self.main_model:
                if self.persistent:
                    self._touch_model(self.vision_model, keep_alive=self.keep_alive, label="vision")
                else:
                    self._touch_model(self.vision_model, keep_alive=0, label="vision")
        elif profile_name == "vision":
            self._touch_model(self.vision_model, keep_alive=self.keep_alive, label="vision")
            if self.main_model and self.main_model != self.vision_model:
                if self.persistent:
                    self._touch_model(self.main_model, keep_alive=self.keep_alive, label="main")
                else:
                    self._touch_model(self.main_model, keep_alive=0, label="main")

        self._active_profile = profile_name

    def _touch_model(self, model: str, keep_alive: int, label: str) -> None:
        if not model:
            return
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "ping"}],
            "stream": False,
            "keep_alive": keep_alive,
        }
        endpoint = f"{self.host}/api/chat"
        try:
            response = requests.post(endpoint, json=payload, timeout=self.timeout_s)
            response.raise_for_status()
            action = "mantener" if keep_alive != 0 else "descargar"
            logger.info("✅ Swarm {}: {} ({})", action, model, label)
        except Exception as exc:
            logger.warning("⚠️ Swarm fallo tocando {} ({}): {}", model, label, exc)

    @staticmethod
    def _load_config(config_path: str) -> Dict[str, Any]:
        if not yaml:
            return {}
        if not os.path.exists(config_path):
            return {}
        try:
            with open(config_path, "r", encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            return data if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("No se pudo leer {}: {}", config_path, exc)
            return {}

    @staticmethod
    def _parse_bool(value: Optional[str], default: bool) -> bool:
        if value is None:
            return bool(default)
        return str(value).strip().lower() in {"1", "true", "yes", "on"}

    @staticmethod
    def _parse_int(value: Optional[str], default: int) -> int:
        if value is None:
            return int(default)
        try:
            return int(str(value).strip())
        except Exception:
            return int(default)
