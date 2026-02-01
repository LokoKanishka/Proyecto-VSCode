import logging
import subprocess
from typing import List

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class GitWorker(BaseWorker):
    """Operaciones Git seguras mediante subprocesos."""

    SAFE_COMMANDS = {"status", "diff", "log", "add", "commit", "branch"}

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        action = message.content
        if action not in self.SAFE_COMMANDS:
            await self.send_error(message, f"Comando Git no permitido: {action}")
            return

        args = message.data.get("args", [])
        if not isinstance(args, list):
            args = [str(args)]
        cmd = ["git", action, *args]
        cwd = message.data.get("cwd", ".")

        stdout, stderr, exit_code = self._run(cmd, cwd)
        await self.send_response(
            message,
            "Comando Git ejecutado.",
            {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "cmd": cmd},
        )

    def _run(self, cmd: List[str], cwd: str):
        try:
            proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)
            return proc.stdout, proc.stderr, proc.returncode
        except Exception as exc:
            logger.exception("Error ejecutando Git")
            return "", str(exc), 1
