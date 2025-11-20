import subprocess
import webbrowser
import logging
import platform
import pyautogui
import time
from pathlib import Path
from typing import List, Optional

log = logging.getLogger("LucyTools")

def abrir_aplicacion(nombre: str) -> str:
    """
    Intenta abrir una aplicación por nombre.
    """
    log.info(f"Tool: abrir_aplicacion({nombre})")
    
    # Normalización básica
    nombre = nombre.lower().strip()
    
    try:
        if platform.system() == "Linux":
            # Intentar con subprocess y nohup para que no bloquee
            subprocess.Popen(["nohup", nombre], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return f"Abrí la aplicación {nombre}."
        else:
            return "Error: Sistema operativo no soportado para abrir apps por ahora."
    except FileNotFoundError:
        return f"No encontré la aplicación '{nombre}' en el sistema."
    except Exception as e:
        log.error(f"Error abriendo app: {e}")
        return f"Tuve un error al intentar abrir {nombre}."

def abrir_url(url: str) -> str:
    """
    Abre una URL en el navegador predeterminado.
    """
    log.info(f"Tool: abrir_url({url})")
    
    if not url.startswith("http"):
        url = "https://" + url
        
    try:
        webbrowser.open(url)
        return f"Abrí la página {url}."
    except Exception as e:
        log.error(f"Error abriendo URL: {e}")
        return "No pude abrir el navegador."

def tomar_captura() -> str:
    """
    Toma una captura de pantalla y la guarda.
    """
    log.info("Tool: tomar_captura()")
    
    pictures_dir = Path.home() / "Pictures" / "LucyScreenshots"
    pictures_dir.mkdir(parents=True, exist_ok=True)
    
    filename = f"screenshot_{int(time.time())}.png"
    filepath = pictures_dir / filename
    
    try:
        pyautogui.screenshot(str(filepath))
        return f"Tomé una captura y la guardé en {filepath}."
    except Exception as e:
        log.error(f"Error tomando captura: {e}")
        # Fallback si no hay display (headless) o error de pyautogui
        return "No pude tomar la captura de pantalla."

def escribir_texto(texto: str) -> str:
    """
    Escribe texto simulando el teclado.
    """
    log.info(f"Tool: escribir_texto({len(texto)} chars)")
    
    try:
        pyautogui.write(texto, interval=0.05)
        return "Escribí el texto."
    except Exception as e:
        log.error(f"Error escribiendo texto: {e}")
        return "No pude escribir el texto."

def execute_tool(tool_name: str, args: List[str]) -> str:
    """
    Dispatcher central para ejecutar herramientas.
    """
    log.info(f"Ejecutando tool: {tool_name} con args: {args}")
    
    if tool_name == "abrir_aplicacion":
        if not args: return "Falta el nombre de la aplicación."
        return abrir_aplicacion(args[0])
        
    elif tool_name == "abrir_url":
        if not args: return "Falta la URL."
        return abrir_url(args[0])
        
    elif tool_name == "tomar_captura":
        return tomar_captura()
        
    elif tool_name == "escribir_texto":
        if not args: return "Falta el texto para escribir."
        return escribir_texto(" ".join(args)) # Unir args por si el LLM los separó
        
    else:
        return f"No conozco la herramienta '{tool_name}'."
