import logging
import subprocess
import webbrowser
import platform
import pyautogui
import time
from pathlib import Path
from typing import List, Callable, Dict

class ToolManager:
    def __init__(self):
        self.log = logging.getLogger("ToolManager")
        self.tools: Dict[str, Callable] = {
            "abrir_aplicacion": self.abrir_aplicacion,
            "abrir_url": self.abrir_url,
            "tomar_captura": self.tomar_captura,
            "escribir_texto": self.escribir_texto,
        }

    def execute(self, tool_name: str, args: List[str]) -> str:
        self.log.info(f"Ejecutando tool: {tool_name} con args: {args}")
        
        if tool_name not in self.tools:
            return f"No conozco la herramienta '{tool_name}'."
            
        func = self.tools[tool_name]
        try:
            # Adapt arguments based on function signature if needed
            # For now, specific handling per tool in the dispatcher was simple,
            # but here we map args list to function arguments.
            
            if tool_name == "abrir_aplicacion":
                if not args: return "Falta el nombre de la aplicación."
                return func(args[0])
            elif tool_name == "abrir_url":
                if not args: return "Falta la URL."
                return func(args[0])
            elif tool_name == "tomar_captura":
                return func()
            elif tool_name == "escribir_texto":
                if not args: return "Falta el texto para escribir."
                return func(" ".join(args))
            else:
                return func(*args)
        except Exception as e:
            self.log.error(f"Error ejecutando {tool_name}: {e}")
            return f"Error al ejecutar {tool_name}: {str(e)}"

    def abrir_aplicacion(self, nombre: str) -> str:
        self.log.info(f"Tool: abrir_aplicacion({nombre})")
        nombre = nombre.lower().strip()
        
        try:
            if platform.system() == "Linux":
                subprocess.Popen(["nohup", nombre], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return f"Abrí la aplicación {nombre}."
            else:
                return "Error: Sistema operativo no soportado para abrir apps por ahora."
        except FileNotFoundError:
            return f"No encontré la aplicación '{nombre}' en el sistema."
        except Exception as e:
            self.log.error(f"Error abriendo app: {e}")
            return f"Tuve un error al intentar abrir {nombre}."

    def abrir_url(self, url: str) -> str:
        self.log.info(f"Tool: abrir_url({url})")
        if not url.startswith("http"):
            url = "https://" + url
        try:
            webbrowser.open(url)
            return f"Abrí la página {url}."
        except Exception as e:
            self.log.error(f"Error abriendo URL: {e}")
            return "No pude abrir el navegador."

    def tomar_captura(self) -> str:
        self.log.info("Tool: tomar_captura()")
        pictures_dir = Path.home() / "Pictures" / "LucyScreenshots"
        pictures_dir.mkdir(parents=True, exist_ok=True)
        filename = f"screenshot_{int(time.time())}.png"
        filepath = pictures_dir / filename
        
        try:
            pyautogui.screenshot(str(filepath))
            return f"Tomé una captura y la guardé en {filepath}."
        except Exception as e:
            self.log.error(f"Error tomando captura: {e}")
            return "No pude tomar la captura de pantalla."

    def escribir_texto(self, texto: str) -> str:
        self.log.info(f"Tool: escribir_texto({len(texto)} chars)")
        try:
            pyautogui.write(texto, interval=0.05)
            return "Escribí el texto."
        except Exception as e:
            self.log.error(f"Error escribiendo texto: {e}")
            return "No pude escribir el texto."
