import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class LoraManager:
    """
    Gestor liviano de LoRAs. Guarda alias -> modelo Ollama y marca LoRA activa.
    """

    def __init__(self):
        self._loras: Dict[str, str] = {}
        self._active: Optional[str] = None

    def register(self, name: str, model: str) -> None:
        self._loras[name] = model

    def activate(self, name: str) -> bool:
        if name not in self._loras:
            logger.warning("LoRA no registrada: %s", name)
            return False
        self._active = name
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
