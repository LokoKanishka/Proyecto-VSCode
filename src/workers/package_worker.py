import logging
import subprocess
import sys
from typing import List

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class PackageWorker(BaseWorker):
    """Gestor básico de paquetes (pip) con comandos permitidos."""

    SAFE_ACTIONS = {"install", "uninstall", "show", "list"}

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        action = message.content
        if action not in self.SAFE_ACTIONS:
            await self.send_error(message, f"Acción de paquetes no permitida: {action}")
            return

        args = message.data.get("args", [])
        if not isinstance(args, list):
            args = [str(args)]

        cmd = [sys.executable, "-m", "pip", action, *args]
        stdout, stderr, exit_code = self._run(cmd)
        await self.send_response(
            message,
            "Operación de paquetes completada.",
            {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "cmd": cmd},
        )

    def _run(self, cmd: List[str]):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return proc.stdout, proc.stderr, proc.returncode
        except Exception as exc:
            logger.exception("Error en PackageWorker")
            return "", str(exc), 1
