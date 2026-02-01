import os
import time
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
        self._active_models: set[str] = set()
        self._force_keep_alive: Optional[int] = None
        self._last_usage: Optional[float] = None
        self._pressure_mode = False
        self.worker_profiles: Dict[str, str] = {}
        lora_targets_raw = os.getenv("LUCY_LORA_TARGETS", "chat_worker,code_worker")
        self._lora_targets = {item.strip() for item in lora_targets_raw.split(",") if item.strip()}
        self._last_lora_prune = 0.0

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
            self._touch_model(self.main_model, keep_alive=self._current_keep_alive(), label="main")
            if not self._pressure_mode and self.vision_model and self.vision_model != self.main_model:
                if self.persistent:
                    self._touch_model(self.vision_model, keep_alive=self._current_keep_alive(), label="vision")
                else:
                    self._touch_model(self.vision_model, keep_alive=0, label="vision")
        elif profile_name == "vision":
            self._touch_model(self.vision_model, keep_alive=self._current_keep_alive(), label="vision")
            if not self._pressure_mode and self.main_model and self.main_model != self.vision_model:
                if self.persistent:
                    self._touch_model(self.main_model, keep_alive=self._current_keep_alive(), label="main")
                else:
                    self._touch_model(self.main_model, keep_alive=0, label="main")

        self._active_profile = profile_name

    def auto_manage_vram(self, usage: float | None) -> None:
        """Decide perfil según uso de VRAM."""
        if usage is None:
            return
        self._last_usage = usage
        self._maybe_prune_loras()
        high = float(os.getenv("LUCY_VRAM_HIGH", "0.88"))
        low = float(os.getenv("LUCY_VRAM_LOW", "0.72"))
        preferred = os.getenv("LUCY_SWARM_PREFERRED_PROFILE", "general")
        force = os.getenv("LUCY_SWARM_FORCE_PROFILE")

        if force in {"general", "vision"}:
            self.set_profile(force)
            return
        if usage >= high:
            self._pressure_mode = True
            self._force_keep_alive = int(os.getenv("LUCY_SWARM_PRESSURE_KEEP_ALIVE", "30"))
            self.set_profile("general")
            self._unload_inactive_models({self.main_model})
            return
        if usage <= low and preferred in {"general", "vision"}:
            self._pressure_mode = False
            self._force_keep_alive = None
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
            if keep_alive != 0:
                self._active_models.add(model)
            else:
                self._active_models.discard(model)
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
            self._active_models.discard(model)
        except Exception as exc:
            logger.warning("⚠️ Swarm no pudo descargar {}: {}", model, exc)

    def load_model(self, model: str) -> None:
        if not model:
            return
        self._touch_model(model, keep_alive=self._current_keep_alive(), label="manual")

    def set_worker_profiles(self, profiles: Dict[str, str]) -> None:
        """Asocia worker -> modelo (para gestión manual)."""
        self.worker_profiles = profiles

    def swap_for_worker(self, worker: str) -> None:
        """Carga modelo asociado a un worker (si existe)."""
        model = self._resolve_model_for_worker(worker)
        if model:
            self._touch_model(model, keep_alive=self._current_keep_alive(), label=f"worker:{worker}")
            if worker in self._lora_targets and self.lora.active():
                self.lora.touch(self.lora.active())

    def register_lora(self, name: str, model: str) -> None:
        self.lora.register(name, model)

    def activate_lora(self, name: str) -> bool:
        return self.lora.activate(name)

    def deactivate_lora(self) -> None:
        self.lora.deactivate()

    def _resolve_model_for_worker(self, worker: str) -> Optional[str]:
        if worker in self._lora_targets and self.lora.active():
            model = self.lora.list().get(self.lora.active())
            if model:
                return model
        if worker in self.worker_profiles:
            return self.worker_profiles[worker]
        if worker == "vision_worker":
            return self.vision_model
        return self.main_model

    def _current_keep_alive(self) -> int:
        return self._force_keep_alive if self._force_keep_alive is not None else self.keep_alive

    def _unload_inactive_models(self, keep: set[str]) -> None:
        keep_models = {m for m in keep if m}
        if not keep_models:
            return
        for model in list(self._active_models):
            if model not in keep_models:
                self.unload_model(model)

    def _maybe_prune_loras(self) -> None:
        now = time.time()
        if now - self._last_lora_prune < float(os.getenv("LUCY_LORA_PRUNE_INTERVAL_S", "60")):
            return
        self._last_lora_prune = now
        idle_s = float(os.getenv("LUCY_LORA_IDLE_S", "600"))
        evict_s = float(os.getenv("LUCY_LORA_EVICT_S", "1800"))
        result = self.lora.prune(idle_s=idle_s, evict_s=evict_s)
        if result.get("evicted"):
            logger.info("🧹 LoRAs evictadas: {}", ",".join(result["evicted"]))

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
