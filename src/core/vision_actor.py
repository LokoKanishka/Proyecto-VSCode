"""
src/core/vision_actor.py
Placeholder for Vision Service migration.
"""
from src.core.base_worker import BaseWorker

class VisionService(BaseWorker):
    def __init__(self, worker_id, bus):
        super().__init__(worker_id, bus)
    
    async def start(self):
        await super().start()
        logger.info("👁️ Vision Service Iniciado (Placeholder Avanzado)")
        # TODO: Integrar pipeline de Set-of-Mark (SoM) real aquí.
        # Por ahora, nos mantenemos a la espera de comandos en el bus.
        pass

    async def handle_vision_request(self, message):
        """Manejar solicitudes de análisis visual."""
        # Stub para futura implementación
        pass
