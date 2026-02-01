import os
from typing import Any, Dict, Optional

import requests
try:
    from loguru import logger
except Exception:  # pragma: no cover - fallback for minimal envs
    import logging

    class _LoggerShim:
        def __init__(self, base_logger: logging.Logger):
            self._logger = base_logger

        def _log(self, level: int, message: str, *args: Any) -> None:
            if args:
                message = message.replace("{}", "%s")
                self._logger.log(level, message, *args)
            else:
                self._logger.log(level, message)

        def debug(self, message: str, *args: Any) -> None:
            self._log(logging.DEBUG, message, *args)

        def info(self, message: str, *args: Any) -> None:
            self._log(logging.INFO, message, *args)

        def warning(self, message: str, *args: Any) -> None:
            self._log(logging.WARNING, message, *args)

        def error(self, message: str, *args: Any) -> None:
            self._log(logging.ERROR, message, *args)

    logger = _LoggerShim(logging.getLogger(__name__))

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from src.engine.lora_manager import LoraManager

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
        self.lora = LoraManager()

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

    def auto_manage_vram(self, usage: float | None) -> None:
        """Decide perfil según uso de VRAM."""
        if usage is None:
            return
        high = float(os.getenv("LUCY_VRAM_HIGH", "0.88"))
        low = float(os.getenv("LUCY_VRAM_LOW", "0.72"))
        preferred = os.getenv("LUCY_SWARM_PREFERRED_PROFILE", "general")
        force = os.getenv("LUCY_SWARM_FORCE_PROFILE")

        if force in {"general", "vision"}:
            self.set_profile(force)
            return
        if usage >= high:
            self.set_profile("general")
            return
        if usage <= low and preferred in {"general", "vision"}:
            self.set_profile(preferred)

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

    def unload_model(self, model: str) -> None:
        if not model:
            return
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "unload"}],
            "stream": False,
            "keep_alive": 0,
        }
        try:
            response = requests.post(f"{self.host}/api/chat", json=payload, timeout=self.timeout_s)
            response.raise_for_status()
            logger.info("🧹 Swarm descargó modelo: {}", model)
        except Exception as exc:
            logger.warning("⚠️ Swarm no pudo descargar {}: {}", model, exc)

    def load_model(self, model: str) -> None:
        if not model:
            return
        self._touch_model(model, keep_alive=self.keep_alive, label="manual")

    def set_worker_profiles(self, profiles: Dict[str, str]) -> None:
        """Asocia worker -> modelo (para gestión manual)."""
        self.worker_profiles = profiles

    def swap_for_worker(self, worker: str) -> None:
        """Carga modelo asociado a un worker (si existe)."""
        model = getattr(self, "worker_profiles", {}).get(worker)
        if model:
            self.load_model(model)

    def register_lora(self, name: str, path: str) -> None:
        self.lora.register(name, path)

    def activate_lora(self, name: str) -> bool:
        return self.lora.activate(name)

    def deactivate_lora(self) -> None:
        self.lora.deactivate()

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
