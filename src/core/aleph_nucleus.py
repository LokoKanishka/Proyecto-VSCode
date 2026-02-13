"""
LUCY ALEPH CORE - Módulo de orquestación de hardware y agentes.
Ubicación: src/core/aleph_nucleus.py
"""
import ray
import pynvml
import lancedb
import asyncio
import json
import os
from loguru import logger
from datetime import datetime
from typing import Dict, Any

# Configuración de límites y rutas
GPU_THRESHOLD = 0.85
MEMORY_PATH = "data/aleph_memory.lance"

@ray.remote(num_gpus=1, namespace="lucy")
class AlephNucleus:
    def __init__(self):
        # Inicializar NVIDIA Management Library
        try:
            pynvml.nvmlInit()
            self.gpu_handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            self.has_gpu = True
            logger.info("⚡ NVML Initialized based on RTX 5090 architecture spec.")
        except Exception as e:
            logger.error(f"Fallo al inicializar NVML: {e}")
            self.has_gpu = False

        # Conexión a la base de datos vectorial LanceDB
        os.makedirs(os.path.dirname(MEMORY_PATH), exist_ok=True)
        self.db = lancedb.connect(MEMORY_PATH)
        self._ensure_tables()
        
        # Estado interno de la entidad
        self.sovereignty_index = 1.0
        logger.info("⚡ LUCY ALEPH NUCLEUS: ONLINE Y SOBERANO")

    def _ensure_tables(self):
        if "interactions" not in self.db.table_names():
            # Esquema inicial para memoria semántica
            # LanceDB detecta el esquema automáticamente del primer dato si no se especifica
            self.db.create_table("interactions", data=[{
                "vector": [0.0] * 384,
                "text": "SYSTEM_INITIALIZED",
                "timestamp": datetime.now().isoformat(),
                "metadata": json.dumps({"status": "sovereign"})
            }])

    async def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Captura de métricas en tiempo real de la RTX 5090."""
        if not self.has_gpu:
            return {"error": "NVIDIA GPU not detected"}

        try:
            info = pynvml.nvmlDeviceGetMemoryInfo(self.gpu_handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(self.gpu_handle)
            try:
                power = pynvml.nvmlDeviceGetPowerUsage(self.gpu_handle) / 1000.0
            except:
                power = 0.0
            
            try:
                temp = pynvml.nvmlDeviceGetTemperature(self.gpu_handle, pynvml.NVML_TEMPERATURE_GPU)
            except:
                temp = 0.0

            return {
                "vram": {"used": info.used // 1024**2, "total": info.total // 1024**2},
                "utilization": util.gpu,
                "power": round(power, 2),
                "temp": temp,
                "status": "CRITICAL" if util.gpu > GPU_THRESHOLD * 100 else "OPTIMAL"
            }
        except Exception as e:
            logger.error(f"Telemetry error: {e}")
            return {"error": str(e)}

    async def save_thought(self, text: str, vector: list):
        """Almacena un fragmento de pensamiento en la memoria persistente."""
        try:
            table = self.db.open_table("interactions")
            table.add([{
                "vector": vector,
                "text": text,
                "timestamp": datetime.now().isoformat(),
                "metadata": json.dumps({"source": "thought_engine"})
            }])
            return True
        except Exception as e:
            logger.error(f"Failed to save thought: {e}")
            return False

async def start_nucleus():
    """Lanzador del núcleo soberano."""
    if not ray.is_initialized():
        ray.init(address="auto", ignore_reinit_error=True)
    return AlephNucleus.remote()
