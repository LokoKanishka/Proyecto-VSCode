from dataclasses import dataclass


@dataclass
class ResourceManager:
    """Monitorea uso de GPU/RAM y decide cuándo limitar workers."""

    gpu_threshold: float = 0.85
    last_gpu_usage: float | None = None

    def update_gpu_usage(self, usage: float | None):
        self.last_gpu_usage = usage

    def is_gpu_overloaded(self) -> bool:
        if self.last_gpu_usage is None:
            return False
        return self.last_gpu_usage >= self.gpu_threshold
