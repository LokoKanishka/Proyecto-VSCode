import logging
import os
import subprocess
import tempfile
import sys
from typing import List, Optional, Tuple

from src.core.base_worker import BaseWorker
from src.core.types import LucyMessage, MessageType

logger = logging.getLogger(__name__)


class CodeWorker(BaseWorker):
    """Ejecuta código en sandbox temporal con lint básico."""

    def __init__(self, worker_id: str, bus):
        super().__init__(worker_id, bus)

    async def handle_message(self, message: LucyMessage):
        if message.type != MessageType.COMMAND:
            return

        if message.content == "run_tests":
            base_path = (message.data or {}).get("path", ".")
            await self._handle_tests(message, base_path)
            return

        if message.content == "lint":
            base_path = (message.data or {}).get("path", ".")
            await self._handle_lint(message, base_path)
            return

        payload_code = message.data.get("code") if isinstance(message.data, dict) else None
        prompt = (payload_code or message.content).strip()
        logger.info("🐍 CodeWorker procesando petición de código: %s", prompt[:80])

        allow_unsafe = bool(message.data.get("allow_unsafe", False)) if isinstance(message.data, dict) else False
        reply_body, reply_data = self._execute_prompt(prompt, allow_unsafe=allow_unsafe)
        await self.send_response(message, reply_body, reply_data)

    def _execute_prompt(self, prompt: str, allow_unsafe: bool = False) -> Tuple[str, dict]:
        normalized = prompt.lower()
        if "fibonacci" in normalized:
            sequence = self._fibonacci(10)
            return (
                f"Fibonacci(10) = {sequence[-1]} | Serie: {sequence}",
                {"script": prompt, "mode": "simulated"},
            )

        code = prompt
        if not code:
            return ("No recibí código para ejecutar.", {"script": ""})
        if not allow_unsafe and self._is_potentially_unsafe(code):
            return ("Código bloqueado por política de seguridad.", {"script": code, "blocked": True})

        stdout, stderr, exit_code, lint = self._run_python(code)
        summary = "Ejecución completada."
        if exit_code != 0:
            summary = "La ejecución devolvió errores."
        reply = (
            f"{summary}\n"
            f"exit_code={exit_code}\n"
            f"stdout:\n{stdout}\n"
            f"stderr:\n{stderr}"
        )
        return reply, {
            "script": code,
            "exit_code": exit_code,
            "stdout": stdout,
            "stderr": stderr,
            "lint": lint,
        }

    def _fibonacci(self, n: int) -> List[int]:
        seq = [0, 1]
        while len(seq) < n:
            seq.append(seq[-1] + seq[-2])
        return seq[:n]

    def _run_python(self, code: str, timeout_s: int = 6) -> Tuple[str, str, int, Optional[str]]:
        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = os.path.join(tmpdir, "snippet.py")
            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(code)

            lint = None
            try:
                lint = subprocess.check_output(
                    [sys.executable, "-m", "py_compile", script_path],
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=timeout_s,
                )
            except subprocess.CalledProcessError as exc:
                lint = exc.output
            except Exception:
                lint = None

            try:
                proc = subprocess.run(
                    [sys.executable, script_path],
                    capture_output=True,
                    text=True,
                    timeout=timeout_s,
                )
                return proc.stdout, proc.stderr, proc.returncode, lint
            except subprocess.TimeoutExpired:
                return "", "Timeout ejecutando el script.", 124, lint

    async def _handle_tests(self, message: LucyMessage, base_path: str) -> None:
        stdout, stderr, exit_code = self._run_command(
            [sys.executable, "-m", "pytest", "-q"],
            cwd=base_path,
            timeout_s=120,
        )
        await self.send_response(
            message,
            "Ejecución de tests completada.",
            {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "path": base_path},
        )

    async def _handle_lint(self, message: LucyMessage, base_path: str) -> None:
        stdout, stderr, exit_code = self._run_command(
            [sys.executable, "-m", "flake8", "."],
            cwd=base_path,
            timeout_s=60,
        )
        await self.send_response(
            message,
            "Lint completado.",
            {"stdout": stdout, "stderr": stderr, "exit_code": exit_code, "path": base_path},
        )

    def _run_command(self, cmd: List[str], cwd: str, timeout_s: int = 60):
        try:
            proc = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
            return proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            return "", "Timeout ejecutando el comando.", 124
        except Exception as exc:
            return "", str(exc), 1

    def _is_potentially_unsafe(self, code: str) -> bool:
        lowered = code.lower()
        blocklist = ["import os", "import subprocess", "shutil", "socket", "open("]
        return any(token in lowered for token in blocklist)
