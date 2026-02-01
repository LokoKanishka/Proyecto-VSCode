from dataclasses import dataclass, field
import subprocess
from typing import Dict, Optional


@dataclass
class ResourceManager:
    """Monitorea uso de GPU/RAM y decide cuándo limitar workers."""

    gpu_threshold: float = 0.85
    last_gpu_usage: float | None = None
    gpu_budget_mb: int = 32000
    worker_budgets: Dict[str, int] = field(default_factory=dict)
    active_workers: Dict[str, int] = field(default_factory=dict)

    def refresh_gpu_usage(self) -> Optional[float]:
        """Consulta nvidia-smi para actualizar el uso de GPU si está disponible."""
        try:
            output = subprocess.check_output(
                ["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip().splitlines()
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None
        max_usage = 0.0
        for line in output:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 2:
                continue
            try:
                used = float(parts[0])
                total = float(parts[1])
            except ValueError:
                continue
            if total <= 0:
                continue
            max_usage = max(max_usage, used / total)
        if max_usage:
            self.last_gpu_usage = max_usage
        return self.last_gpu_usage

    def update_gpu_usage(self, usage: float | None):
        self.last_gpu_usage = usage

    def is_gpu_overloaded(self) -> bool:
        if self.last_gpu_usage is None:
            return False
        return self.last_gpu_usage >= self.gpu_threshold

    def register_worker_budget(self, worker_id: str, gpu_mb: int) -> None:
        self.worker_budgets[worker_id] = gpu_mb

    def can_schedule(self, worker_id: str) -> bool:
        budget = self.worker_budgets.get(worker_id)
        if budget is None:
            return True
        used = sum(self.active_workers.values())
        return used + budget <= self.gpu_budget_mb

    def mark_worker_active(self, worker_id: str) -> None:
        budget = self.worker_budgets.get(worker_id, 0)
        self.active_workers[worker_id] = budget

    def mark_worker_idle(self, worker_id: str) -> None:
        self.active_workers.pop(worker_id, None)
