import asyncio
import logging
import os
import pty

from src.core.base_worker import BaseWorker
from src.core.lucy_types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class ShellWorker(BaseWorker):
    """Ejecuta comandos de shell con timeout y captura de salida."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)
        self.blocklist = ["rm -rf", "mkfs", ":(){", "dd if=", "shutdown", "reboot"]

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        command = message.data.get("command") if isinstance(message.data, dict) else None
        timeout = float(message.data.get("timeout", 30.0)) if isinstance(message.data, dict) else 30.0
        allow_unsafe = bool(message.data.get("allow_unsafe", False)) if isinstance(message.data, dict) else False
        use_pty = bool(message.data.get("use_pty", False)) if isinstance(message.data, dict) else False

        if not command:
            await self.send_error(message, "No recibí el comando para ejecutar.")
            return
        if not allow_unsafe and not self._is_safe(command):
            await self.send_error(message, "Comando bloqueado por política de seguridad.")
            return

        logger.info("🖥️ ShellWorker ejecutando: %s", command)
        stdout, stderr, exit_code = await self._run_command(command, timeout=timeout, use_pty=use_pty)
        await self.send_response(
            message,
            "Comando ejecutado.",
            {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "command": command},
        )

    async def _run_command(self, command: str, timeout: float = 30.0, use_pty: bool = False):
        try:
            if use_pty:
                return await self._run_command_pty(command, timeout)
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return "", "Timeout ejecutando el comando.", 124

            stdout_text = stdout.decode(errors="replace") if stdout else ""
            stderr_text = stderr.decode(errors="replace") if stderr else ""
            return stdout_text, stderr_text, proc.returncode
        except Exception as exc:
            logger.exception("Error en ShellWorker")
            return "", str(exc), 1

    async def _run_command_pty(self, command: str, timeout: float = 30.0):
        """Ejecuta comando en pseudo-TTY para herramientas interactivas."""
        loop = asyncio.get_running_loop()
        master_fd, slave_fd = pty.openpty()
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                start_new_session=True,
            )
            os.close(slave_fd)
            output = []

            async def _reader():
                while True:
                    try:
                        data = await loop.run_in_executor(None, os.read, master_fd, 1024)
                    except OSError:
                        break
                    if not data:
                        break
                    output.append(data.decode(errors="replace"))

            reader_task = asyncio.create_task(_reader())
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                return "", "Timeout ejecutando el comando.", 124
            await reader_task
            return "".join(output), "", proc.returncode or 0
        finally:
            try:
                os.close(master_fd)
            except OSError:
                pass

    def _is_safe(self, command: str) -> bool:
        lowered = command.lower()
        return not any(token in lowered for token in self.blocklist)
