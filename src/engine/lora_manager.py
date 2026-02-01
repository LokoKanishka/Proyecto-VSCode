import logging
import time
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class LoraManager:
    """
    Gestor liviano de LoRAs. Guarda alias -> modelo Ollama y marca LoRA activa.
    """

    def __init__(self):
        self._loras: Dict[str, str] = {}
        self._active: Optional[str] = None
        self._last_used: Dict[str, float] = {}
        self._registered_at: Dict[str, float] = {}

    def register(self, name: str, model: str) -> None:
        self._loras[name] = model
        now = time.time()
        self._registered_at[name] = now
        self._last_used.setdefault(name, now)

    def activate(self, name: str) -> bool:
        if name not in self._loras:
            logger.warning("LoRA no registrada: %s", name)
            return False
        self._active = name
        self.touch(name)
        logger.info("LoRA activa: %s", name)
        return True

    def deactivate(self) -> None:
        if self._active:
            logger.info("LoRA desactivada: %s", self._active)
        self._active = None

    def active(self) -> Optional[str]:
        return self._active

    def list(self) -> Dict[str, str]:
        return dict(self._loras)

    def touch(self, name: str) -> None:
        if name in self._loras:
            self._last_used[name] = time.time()

    def prune(self, idle_s: float, evict_s: float) -> Dict[str, list[str]]:
        removed: list[str] = []
        now = time.time()
        if self._active and idle_s > 0:
            last = self._last_used.get(self._active, 0.0)
            if now - last >= idle_s:
                logger.info("LoRA inactiva por idle: %s", self._active)
                self._active = None
        if evict_s > 0:
            for name in list(self._loras.keys()):
                last = self._last_used.get(name, self._registered_at.get(name, 0.0))
                if now - last >= evict_s:
                    self._loras.pop(name, None)
                    self._last_used.pop(name, None)
                    self._registered_at.pop(name, None)
                    removed.append(name)
        return {"evicted": removed}
