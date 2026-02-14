"""
src/workers/nucleus.py
El Corazón del Sistema (Hardware & Soberanía).
Reemplaza al AlephNucleus basado en Ray.
"""
import asyncio
import json
import os
import pynvml
from datetime import datetime
from loguru import logger
from typing import Dict, Any

from src.core.base_worker import BaseWorker
from src.core.lucy_types import MessageType, LucyMessage, WorkerType
from src.core.persistence import Hippocampus

GPU_THRESHOLD = 0.85

class NucleusWorker(BaseWorker):
    def __init__(self, bus):
        super().__init__(WorkerType.MANAGER, bus) # Manager acts as Nucleus
        self.hippocampus = Hippocampus()
        self.has_gpu = False
        self.gpu_handle = None
        
        # Init NVML
        try:
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.has_gpu = True
            logger.info("⚡ Nucleus: NVML Initialized (RTX 5090 detected).")
        except Exception as e:
            logger.warning(f"Nucleus: No GPU telemetry available ({e}).")

    async def start(self):
        await super().start()
        # Iniciar latido de telemetría
        asyncio.create_task(self._telemetry_loop())

    async def _telemetry_loop(self):
        """Publica estado del sistema cada segundo."""
        while self.running:
            telemetry = self._get_hardware_telemetry()
            # Publicar evento de telemetría (para UI)
            msg = LucyMessage(
                sender=self.worker_id,
                receiver="broadcast", # Broadcast para que la UI lo escuche via API
                type=MessageType.EVENT,
                content="TELEMETRY_UPDATE",
                data=telemetry
            )
            await self.bus.publish(msg)
            await asyncio.sleep(2.0)

    def _get_hardware_telemetry(self) -> Dict[str, Any]:
        if not self.has_gpu:
            return {"status": "CPU_ONLY"}
        try:
            info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
            return {
                "gpu": {
                    "vram_used": info.used // 1024**2,
                    "vram_total": info.total // 1024**2,
                    "utilization": util.gpu,
                    "temp": temp
                },
                "sovereignty": self.hippocampus.recall() # Breve estado de consciencia
            }
        except Exception:
            return {}

    async def handle_message(self, message: LucyMessage):
        # El Nucleus también puede actuar como orquestador si es necesario
        # Por ahora solo observamos
        pass
