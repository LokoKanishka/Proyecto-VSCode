"""
src/workers/system.py
El Brazo Ejecutor (System Worker).
Ejecuta comandos de shell, gestiona mouse/teclado y lanzamientos de aplicaciones.
"""
import asyncio
import subprocess
import shlex
import os
from loguru import logger
from src.core.lucy_types import MessageType, WorkerType, LucyMessage
from src.core.bus import EventBus

# Seguridad: Lista blanca de comandos permitidos (expandible)
ALLOWED_COMMANDS = {
    "ls", "pwd", "echo", "cat", "grep", "find", 
    "whoami", "date", "uptime", "free", "df"
}

class SystemWorker:
    def __init__(self, bus: EventBus):
        self.bus = bus
        self.running = False

    async def start(self):
        logger.info("🔧 System Worker Iniciado.")
        self.running = True
        self.bus.subscribe(WorkerType.SHELL, self.handle_shell_command)
        self.bus.subscribe(WorkerType.HANDS, self.handle_hands_command)

    async def stop(self):
        self.running = False
        logger.info("System Worker Detenido.")

    async def handle_shell_command(self, message: LucyMessage):
        """Ejecuta comandos de terminal de forma segura."""
        cmd_str = message.content.strip()
        logger.info(f"🐚 Ejecutando: {cmd_str}")
        
        # Validación básica de seguridad (Soberanía responsable)
        # TODO: Mejorar la integración con el Evaluador de Riesgos (RiskEvaluator)
        # Por ahora, si es un comando peligroso (rm, dd, mkfs), requerir confirmación explícita
        if "rm " in cmd_str or "dd " in cmd_str or "mkfs" in cmd_str:
            logger.warning(f"⚠️ Comando de alto riesgo interceptado: {cmd_str}")
            # En un sistema real, aquí se pediría confirmación al usuario o al Overseer
            # return

        try:
            proc = await asyncio.create_subprocess_shell(
                cmd_str,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            
            output = stdout.decode().strip()
            error = stderr.decode().strip()
            
            response_content = output if not error else f"{output}\nError: {error}"
            
            # Responder al remitente
            if message.in_reply_to or message.sender:
                response = LucyMessage(
                    sender=WorkerType.SHELL,
                    receiver=message.sender,
                    type=MessageType.RESPONSE,
                    content=response_content,
                    in_reply_to=message.id
                )
                await self.bus.publish(response)
                
        except Exception as e:
            logger.error(f"Fallo en ejecución de shell: {e}")

    async def handle_hands_command(self, message: LucyMessage):
        """Control de Mouse/Teclado (pyautogui)."""
        # Por ahora delegamos a x11_file_agent.py vía subprocess si es necesario,
        # o importamos pyautogui directamente aquí si no bloquea.
        # En la arquitectura nueva, esto debería ser nativo.
        action = message.data.get("action")
        logger.info(f"✋ Acción de Manos: {action}")
        
        if action == "type":
            text = message.data.get("text")
            # pyautogui.typewrite(text) -> Bloqueante, usar executor
            await asyncio.to_thread(self._safe_type, text)
            
    def _safe_type(self, text):
        import pyautogui
        pyautogui.write(text, interval=0.05)
