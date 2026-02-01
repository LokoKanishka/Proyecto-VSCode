"""
Shim de ToolManager para el pipeline de Lucy Voz.
Mantiene compatibilidad con `LucyOrchestrator` aunque no haya herramientas definidas.
"""

from typing import Any, Iterable
import platform
import webbrowser
import subprocess


class ToolManager:
    def __init__(self, tools: Iterable[Any] | None = None) -> None:
        # Permitimos registrar herramientas en el futuro; hoy no hay implementación.
        self.tools = list(tools or [])

    def execute(self, tool_name: str, args: list[Any] | dict[str, Any] | None = None) -> str:
        """
        Ejecuta una herramienta ficticia. Devuelve un mensaje neutro para evitar fallos.
        """
        params = args or []
        if tool_name == "abrir_url":
            url = params[0] if isinstance(params, list) and params else None
            if not url:
                return "No recibí una URL para abrir."
            webbrowser.open(url)
            return f"Abrí la página {url}"
        if tool_name == "abrir_aplicacion":
            app = params[0] if isinstance(params, list) and params else None
            if not app:
                return "No recibí una aplicación para abrir."
            system = platform.system()
            if system == "Darwin":
                subprocess.Popen(["open", "-a", app])
            elif system == "Windows":
                subprocess.Popen([app], shell=True)
            else:
                subprocess.Popen([app])
            return f"Abrí la aplicación {app}"

        return f"Herramienta '{tool_name}' no está disponible en este entorno."


__all__ = ["ToolManager", "platform", "webbrowser", "subprocess"]
