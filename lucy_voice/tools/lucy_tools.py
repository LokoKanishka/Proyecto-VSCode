"""
Shim de ToolManager para el pipeline de Lucy Voz.
Mantiene compatibilidad con `LucyOrchestrator` aunque no haya herramientas definidas.
"""

from typing import Any, Iterable


class ToolManager:
    def __init__(self, tools: Iterable[Any] | None = None) -> None:
        # Permitimos registrar herramientas en el futuro; hoy no hay implementación.
        self.tools = list(tools or [])

    def execute(self, tool_name: str, args: list[Any] | dict[str, Any] | None = None) -> str:
        """
        Ejecuta una herramienta ficticia. Devuelve un mensaje neutro para evitar fallos.
        """
        return f"Herramienta '{tool_name}' no está disponible en este entorno."


__all__ = ["ToolManager"]
