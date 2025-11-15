"""
lucy_tools.py – Funciones de utilidad para que Lucy pueda actuar como agente
de escritorio (abrir apps, tomar capturas, etc.).

En esta primera versión solo incluimos funciones simples y relativamente seguras.
Más adelante se ampliará con más herramientas y manejo de errores más fino.
"""

from pathlib import Path
import subprocess
from typing import Optional

import pyautogui


def tomar_captura(nombre_archivo: str = "captura_lucy.png",
                  carpeta: Optional[Path] = None) -> Path:
    """
    Toma una captura de pantalla completa y la guarda en la ruta indicada.

    - nombre_archivo: nombre del archivo PNG a crear.
    - carpeta: carpeta donde guardar la captura. Si es None, usa `lucy_voice/tests/`.

    Devuelve:
        Path absoluto al archivo generado.
    """
    if carpeta is None:
        carpeta = Path(__file__).resolve().parent / "tests"

    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_archivo = carpeta / nombre_archivo

    screenshot = pyautogui.screenshot()
    screenshot.save(ruta_archivo)

    return ruta_archivo


def abrir_aplicacion(comando: str) -> subprocess.Popen:
    """
    Abre una aplicación usando un comando de sistema (por ejemplo 'vlc', 'firefox').

    Esta función solo define la llamada. Más adelante se expondrá al LLM
    mediante Tool Calling.

    Devuelve:
        El objeto Popen del proceso lanzado.
    """
    proc = subprocess.Popen(comando.split())
    return proc


def simular_teclado(secuencia: str) -> None:
    """
    Simula una combinación de teclas usando pyautogui.

    Ejemplos:
        - "ctrl+c"
        - "alt+tab"

    Nota: por ahora **NO** ejecuta realmente las teclas para evitar efectos
    no deseados. Solo muestra por pantalla qué se haría. Cuando esté bien
    probado se podrá cambiar a `pyautogui.hotkey(*partes)`.
    """
    partes = [p.strip() for p in secuencia.lower().split("+") if p.strip()]
    if not partes:
        print("[DEBUG] secuencia vacía, no se simulan teclas.")
        return

    print(f"[DEBUG] Simular teclas: {partes}")
    # Futuro:
    # pyautogui.hotkey(*partes)
