import asyncio
import json
import logging
import os
import subprocess
from typing import Optional

try:
    import websockets
    HAS_WEBSOCKETS = True
except Exception:  # pragma: no cover - optional dependency
    HAS_WEBSOCKETS = False

from src.core.base_worker import BaseWorker
from src.core.lucy_types import LucyMessage, MessageType, WorkerType

logger = logging.getLogger(__name__)


class VSCodeWorker(BaseWorker):
    """Control básico de VS Code vía CLI (sin UI)."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)
        self.ws_url = os.getenv("LUCY_VSCODE_WS", "ws://127.0.0.1:8765")
        self.prefer_ws = os.getenv("LUCY_VSCODE_WS_ENABLED", "1").lower() in {"1", "true", "yes"}
        self._ws_backlog = []
        self._ws_backlog_max = int(os.getenv("LUCY_VSCODE_WS_BACKLOG_MAX", "50"))
        self._ws_retries = int(os.getenv("LUCY_VSCODE_WS_RETRIES", "3"))
        self._ws_backoff_s = float(os.getenv("LUCY_VSCODE_WS_BACKOFF_S", "0.5"))
        self._ws_buffer = os.getenv("LUCY_VSCODE_WS_BUFFER", "1").lower() in {"1", "true", "yes"}

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
        if cmd == "insert_text":
            await self._insert_text(message)
            return
        if cmd == "save_file":
            await self._save_file(message)
            return
        if cmd == "run_command":
            await self._run_command(message)
            return
        if cmd == "list_extensions":
            await self._list_extensions(message)
            return
        if cmd == "ws_health":
            await self._ws_health(message)
            return

        await self.send_error(message, f"Comando desconocido: {cmd}")

    async def _open_file(self, message: LucyMessage):
        path = message.data.get("path")
        line = message.data.get("line")
        column = message.data.get("column")
        if not path:
            await self.send_error(message, "Necesito un path de archivo.")
            return
        if self._should_use_ws(message):
            try:
                result = await self._ws_call("openFile", {"path": path, "line": line, "column": column})
                await self.send_response(message, "Archivo abierto en VS Code (WS).", result or {"path": path})
                return
            except Exception as exc:
                await self.send_error(message, f"WS falló: {exc}")
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
            if os.getenv("LUCY_SNAPSHOT_ON_WRITE", "0").lower() in {"1", "true", "yes"}:
                await self.bus.publish(
                    LucyMessage(
                        sender=self.worker_id,
                        receiver=WorkerType.MEMORY,
                        type=MessageType.COMMAND,
                        content="snapshot_files",
                        data={
                            "paths": [path],
                            "metadata": {"source": "vscode_worker"},
                        },
                    )
                )
        except OSError as exc:
            await self.send_error(message, f"No pude escribir el archivo: {exc}")

    async def _insert_text(self, message: LucyMessage):
        text = message.data.get("text")
        if not text:
            await self.send_error(message, "Necesito texto para insertar.")
            return
        if not self._should_use_ws(message):
            await self.send_error(message, "insert_text requiere WebSocket (extensión VS Code).")
            return
        try:
            result = await self._ws_call("insertText", {"text": text})
            await self.send_response(message, "Texto insertado en VS Code (WS).", result or {"chars": len(text)})
        except Exception as exc:
            await self.send_error(message, f"WS falló: {exc}")

    async def _save_file(self, message: LucyMessage):
        if not self._should_use_ws(message):
            await self.send_error(message, "save_file requiere WebSocket (extensión VS Code).")
            return
        try:
            result = await self._ws_call("saveFile", {})
            await self.send_response(message, "Archivo guardado en VS Code (WS).", result or {})
        except Exception as exc:
            await self.send_error(message, f"WS falló: {exc}")

    async def _run_command(self, message: LucyMessage):
        command = message.data.get("command")
        params = message.data.get("params", [])
        if not command:
            await self.send_error(message, "Necesito el comando de VS Code.")
            return
        if not self._should_use_ws(message):
            await self.send_error(message, "run_command requiere WebSocket (extensión VS Code).")
            return
        try:
            result = await self._ws_call("runCommand", {"command": command, "params": params})
            await self.send_response(message, "Comando ejecutado en VS Code (WS).", result or {})
        except Exception as exc:
            await self.send_error(message, f"WS falló: {exc}")

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

    async def _ws_health(self, message: LucyMessage):
        if not self._should_use_ws(message):
            await self.send_error(message, "ws_health requiere WebSocket (extensión VS Code).")
            return
        try:
            result = await self._ws_call("ping", {})
            await self.send_response(message, "WS OK.", result or {})
        except Exception as exc:
            await self.send_error(message, f"WS health falló: {exc}")

    def _should_use_ws(self, message: LucyMessage) -> bool:
        if message.data.get("use_ws") is not None:
            return bool(message.data.get("use_ws"))
        return self.prefer_ws

    async def _ws_call(self, action: str, args: dict):
        if not HAS_WEBSOCKETS:
            raise RuntimeError("Falta dependencia websockets.")
        url = args.pop("ws_url", None) or self.ws_url
        payload = {"type": "command", "action": action, "args": args}
        try:
            return await self._ws_send_with_retries(url, payload)
        except Exception as exc:
            if self._ws_buffer:
                self._enqueue_ws(payload)
                raise RuntimeError(f"WS offline, comando en cola: {exc}")
            raise

    async def _ws_send_with_retries(self, url: str, payload: dict):
        last_exc: Optional[Exception] = None
        for attempt in range(1, self._ws_retries + 1):
            try:
                async with websockets.connect(url) as ws:
                    await self._flush_backlog(ws)
                    await ws.send(json.dumps(payload))
                    raw = await ws.recv()
                data = json.loads(raw)
                if data.get("type") == "error":
                    raise RuntimeError(data.get("error", "Error desconocido"))
                return data.get("result")
            except Exception as exc:
                last_exc = exc
                if attempt < self._ws_retries:
                    await asyncio.sleep(self._ws_backoff_s * attempt)
        raise last_exc or RuntimeError("WS no disponible")

    async def _flush_backlog(self, ws):
        if not self._ws_backlog:
            return
        pending = list(self._ws_backlog)
        self._ws_backlog.clear()
        for item in pending:
            await ws.send(json.dumps(item))
            await ws.recv()

    def _enqueue_ws(self, payload: dict) -> None:
        self._ws_backlog.append(payload)
        if len(self._ws_backlog) > self._ws_backlog_max:
            self._ws_backlog = self._ws_backlog[-self._ws_backlog_max:]
