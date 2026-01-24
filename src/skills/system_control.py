from src.skills.base_skill import BaseSkill
import os
import subprocess
from typing import Dict, Any
from loguru import logger

class SystemControlSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "system_control"

    @property
    def description(self) -> str:
        return "Controla parámetros del sistema como el volumen del audio o la ejecución de aplicaciones locales."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "La acción a realizar: 'volume_up', 'volume_down', 'mute', 'open_app'.",
                    "enum": ["volume_up", "volume_down", "mute", "open_app"]
                },
                "argument": {
                    "type": "string",
                    "description": "Argumento opcional para la acción (ej: nombre de la app para 'open_app')."
                }
            },
            "required": ["action"]
        }

    def execute(self, action: str, argument: str = None) -> str:
        logger.info(f"Ejecutando acción de sistema: {action} (arg: {argument})")
        
        try:
            if action == "volume_up":
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%+"], check=True)
                return "Volumen aumentado al 10% adicional."
            
            elif action == "volume_down":
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "10%-"], check=True)
                return "Volumen disminuido en un 10%."
            
            elif action == "mute":
                subprocess.run(["amixer", "-D", "pulse", "sset", "Master", "toggle"], check=True)
                return "Estado de silencio (mute) alternado."
            
            elif action == "open_app":
                if not argument:
                    return "Error: Se requiere el nombre de la aplicación para abrirla."
                # Usar xdg-open o ejecutar directamente
                subprocess.Popen([argument], start_new_session=True)
                return f"Intentando abrir la aplicación: {argument}."
            
            return "Acción no reconocida."
            
        except Exception as e:
            logger.error(f"Error en SystemControlSkill: {e}")
            return f"Error al ejecutar la acción de sistema: {str(e)}"
