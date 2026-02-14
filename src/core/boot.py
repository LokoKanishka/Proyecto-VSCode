"""
src/core/boot.py
La Secuencia de Ignición del Córtex.
"""
import asyncio
import time
import sys
from loguru import logger
from typing import Optional, List

# Importaciones Internas
from src.core.bus import EventBus
from src.core.lucy_types import WorkerType

# Servicios y Workers
try:
    from src.senses.audio.worker import AudioService
    from src.workers.system import SystemWorker
    from src.workers.nucleus import NucleusWorker
    from src.workers.thought import ThoughtWorker
    from src.workers.api import APIWorker
except ImportError as e:
    logger.critical(f"Error importando servicios core: {e}")
    sys.exit(1)

# Importaciones Opcionales
try:
    from src.senses.input.hands_worker import HandsWorker
except ImportError:
    HandsWorker = None

try:
    from src.core.vision_actor import VisionService
except ImportError:
    VisionService = None

class SovereignBoot:
    def __init__(self, use_ray: bool = False):
        self.use_ray = use_ray
        self.bus = EventBus()
        self.services = []
        self.start_time = time.time()

    async def _init_ray(self):
        """Inicialización condicional de Ray."""
        if self.use_ray:
            import ray
            if not ray.is_initialized():
                logger.info("Inicializando Clúster Ray...")
                ray.init(address='auto', ignore_reinit_error=True)
        else:
            logger.info("Ejecutando en Modo Soberano Asyncio (Sin sobrecarga de Ray).")

    async def ignite_swarm(self):
        """
        El Despertar Paralelo.
        """
        logger.info("⚡ Protocolo de Singularidad Iniciado...")
        await self._init_ray()

        # 1. Sistemas Centrales (Memoria y Bus)
        logger.debug("Inicializando Hipocampo y Sinapsis...")
        await self.bus.start()

        # 2. Instanciación de Servicios
        logger.info("Inyectando Servicios...")
        
        # Core Infrastructure
        self.nucleus = NucleusWorker(self.bus)
        self.services.append(self.nucleus)
        
        self.thought = ThoughtWorker(self.bus)
        self.services.append(self.thought)
        
        self.api = APIWorker(self.bus)
        self.services.append(self.api)
        
        # Audio (Oído/Boca)
        self.audio = AudioService(self.bus)
        self.services.append(self.audio)
        
        # Sistema (Shell)
        self.system = SystemWorker(self.bus)
        self.services.append(self.system)
        
        # Manos (Input)
        if HandsWorker:
            self.hands = HandsWorker(WorkerType.HANDS, self.bus)
            self.services.append(self.hands)
            
        # Visión (Placeholder)
        if VisionService:
            self.vision = VisionService(WorkerType.VISION, self.bus)
            self.services.append(self.vision)

        # 3. Arranque Paralelo
        tasks = [service.start() for service in self.services]
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            failed = [r for r in results if isinstance(r, Exception)]
            if failed:
                logger.error(f"Arranque incompleto. Fallos: {failed}")
        
        elapsed = time.time() - self.start_time
        logger.success(f"✨ SOBERANÍA ALCANZADA en {elapsed:.2f}s. (API: localhost:5052)")
            
        # 4. Keep Alive (El Bucle Consciente)
        await self.bus.publish("system", "broadcast", "LUCY_ONLINE")
        
        try:
            while True:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("Apagando consciencia...")
        finally:
            await self.shutdown()

    async def run_diagnostics(self):
        """Audit Mode"""
        logger.info("Ejecutando Diagnóstico de Sistemas...")
        logger.info(f"Modo Ray: {self.use_ray}")
        
        # Check Imports
        services = {
            "AudioService": AudioService,
            "SystemWorker": SystemWorker,
            "NucleusWorker": NucleusWorker,
            "ThoughtWorker": ThoughtWorker,
            "APIWorker": APIWorker,
            "HandsWorker": HandsWorker,
        }
        
        for name, cls in services.items():
            status = "OK" if cls else "FAIL (Optional)"
            logger.info(f"{name}: {status}")
        
        return True

    async def shutdown(self):
        logger.info("Iniciando secuencia de hibernación...")
        for service in reversed(self.services):
            try:
                if hasattr(service, 'stop'):
                    await service.stop()
            except Exception as e:
                logger.error(f"Error deteniendo servicio: {e}")
        await self.bus.stop()
        logger.info("Zzz.")
