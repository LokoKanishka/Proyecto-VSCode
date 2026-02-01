import logging
import os
import subprocess
from typing import Optional

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class VSCodeWorker(BaseWorker):
    """Control básico de VS Code vía CLI (sin UI)."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        cmd = message.content
        if cmd == "open_file":
            await self._open_file(message)
            return
        if cmd == "write_file":
            await self._write_file(message)
            return
        if cmd == "list_extensions":
            await self._list_extensions(message)
            return

        await self.send_error(message, f"Comando desconocido: {cmd}")

    async def _open_file(self, message: LucyMessage):
        path = message.data.get("path")
        line = message.data.get("line")
        column = message.data.get("column")
        if not path:
            await self.send_error(message, "Necesito un path de archivo.")
            return
        location = path
        if line:
            location = f"{path}:{line}"
            if column:
                location = f"{location}:{column}"
        code_bin = message.data.get("code_bin", "code")
        try:
            subprocess.run([code_bin, "--goto", location], check=False)
            await self.send_response(message, "Archivo abierto en VS Code.", {"path": path})
        except FileNotFoundError:
            await self.send_error(message, "No encontré la CLI de VS Code (code).")

    async def _write_file(self, message: LucyMessage):
        path = message.data.get("path")
        content = message.data.get("content", "")
        mode = message.data.get("mode", "w")
        if not path:
            await self.send_error(message, "Necesito un path de archivo.")
            return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        try:
            with open(path, mode, encoding="utf-8") as fh:
                fh.write(content)
            await self.send_response(message, "Archivo escrito.", {"path": path})
        except OSError as exc:
            await self.send_error(message, f"No pude escribir el archivo: {exc}")

    async def _list_extensions(self, message: LucyMessage):
        code_bin = message.data.get("code_bin", "code")
        try:
            proc = subprocess.run([code_bin, "--list-extensions"], capture_output=True, text=True, check=False)
            await self.send_response(
                message,
                "Extensiones listadas.",
                {"stdout": proc.stdout, "stderr": proc.stderr, "exit_code": proc.returncode},
            )
        except FileNotFoundError:
            await self.send_error(message, "No encontré la CLI de VS Code (code).")
