"""
src/senses/audio/worker.py
La Voz Unificada de Lucy.
Combina escucha (Ear) y habla (Mouth) en un servicio no bloqueante.
"""
import asyncio
import threading
import json
from loguru import logger
from src.core.lucy_types import MessageType, LucyMessage, WorkerType

# Dependencias condicionales
try:
    import sounddevice as sd
    import soundfile as sf
    from faster_whisper import WhisperModel
    HAS_AUDIO = True
except ImportError:
    HAS_AUDIO = False
    logger.warning("Faltan dependencias de audio (sounddevice, faster-whisper). Lucy estará sorda/muda.")

class AudioService:
    def __init__(self, bus):
        self.bus = bus
        self.running = False
        self.model = None
        self._thread = None
        self._loop = None # Bucle principal para callbacks
        self.vad_sensitivity = 3

    async def start(self):
        if not HAS_AUDIO:
            return
        
        self._loop = asyncio.get_running_loop()
        logger.info("🎧 Inicializando Sistema Auditivo...")
        
        # Cargar modelo en un hilo separado para no bloquear el bucle de eventos
        await asyncio.to_thread(self._load_model)
        
        self.running = True
        # Suscribirse a eventos de la boca (TTS)
        self.bus.subscribe(WorkerType.MOUTH, self.handle_speak_command)
        
        # Iniciar bucle de escucha en hilo de fondo
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.success("👂 Oído Abierto.")

    def _load_model(self):
        # Optimizado para RTX 5090 (usar cuda si está disponible, sino cpu/int8)
        device = "cuda" 
        compute_type = "float16"
        
        # Intento de detección de GPU más robusta
        try:
            import torch
            if not torch.cuda.is_available():
                device = "cpu"
                compute_type = "int8"
                logger.warning("GPU no detectada por PyTorch, usando CPU/int8")
        except ImportError:
            # Si no hay torch, intentamos blind faith en cuda si hay driver, o fallback
            try:
                subprocess.run(['nvidia-smi'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            except (FileNotFoundError, subprocess.CalledProcessError):
                device = "cpu"
                compute_type = "int8"
                logger.warning("nvidia-smi no encontrado, usando CPU/int8")

        try:
            self.model = WhisperModel("small", device=device, compute_type=compute_type)
            logger.info(f"Modelo Whisper cargado en {device} ({compute_type}).")
        except Exception as e:
            logger.warning(f"Fallo al cargar en {device} ({e}), cayendo a CPU/int8.")
            self.model = WhisperModel("small", device="cpu", compute_type="int8")

    async def handle_speak_command(self, message: LucyMessage):
        """Manejador de TTS (Text-to-Speech)"""
        text = message.content
        logger.info(f"🗣️ Hablando: {text}")
        
        # Usar mimic3 localmente (subprocess)
        # Se asume que mimic3 está instalado en el sistema o venv
        try:
            proc = await asyncio.create_subprocess_exec(
                "mimic3", "--voice", "es_ES/m-ailabs_low", text, "--stdout",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL
            )
            audio_data, _ = await proc.communicate()
            
            if audio_data and HAS_AUDIO:
                # Reproducción simple
                # TODO: Implementar cola de salida de audio para evitar superposiciones
                pass 
                # Por ahora solo logueamos que se generó
                logger.debug(f"Audio generado ({len(audio_data)} bytes)")
        except FileNotFoundError:
            logger.error("Mimic3 no encontrado. Instalar con: pip install mycroft-mimic3-tts")

    def _listen_loop(self):
        """
        El Bucle del Oído (Thread Separado). 
        Bloquea en lectura de audio, detecta VAD, transcribe y envía al Bus.
        """
        if not HAS_AUDIO: 
            return

        # Configuración de micrófono
        # TODO: Cargar desde config.yaml
        SAMPLE_RATE = 16000
        BLOCK_SIZE = 4096 # chunks

        # Simulación por ahora: En un bucle real, leeríamos de sounddevice
        # y procesaríamos con Silero VAD o WebRTCVAD
        while self.running:
            time.sleep(1) # Placeholder para no quemar CPU en este esqueleto
            
            # Pseudocódigo de detección:
            # audio_chunk = sd.read(BLOCK_SIZE)
            # if is_speech(audio_chunk):
            #    text = self.model.transcribe(audio_chunk)
            #    if text:
            #        msg = LucyMessage(
            #            sender=WorkerType.EAR,
            #            receiver=WorkerType.MANAGER, # O Thought
            #            type=MessageType.EVENT,
            #            content=text
            #        )
            #        self._loop.call_soon_threadsafe(
            #            asyncio.create_task, self.bus.publish(msg)
            #        )

    async def stop(self):
        self.running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        logger.info("Audio Service Detenido.")
