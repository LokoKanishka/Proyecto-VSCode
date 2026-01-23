#!/usr/bin/env python3
"""
check_env.py – Verifica que las dependencias básicas de Lucy-voz estén instaladas.

Se puede ejecutar con:
    python3 lucy_voice/check_env.py
dentro del repo del proyecto.
"""

import importlib

MODULES = [
    ("pipecat", "pipecat-ai"),
    ("faster_whisper", "faster-whisper"),
    ("openwakeword", "openwakeword"),
    ("mimic3_tts", "mycroft-mimic3-tts"),
    ("pyautogui", "pyautogui"),
    ("sounddevice", "sounddevice"),
    ("numpy", "numpy"),
]

def main():
    print("== Chequeo de entorno Lucy-voz ==")
    for module_name, pip_name in MODULES:
        try:
            importlib.import_module(module_name)
            print(f"[OK] {module_name} (pip: {pip_name})")
        except ImportError:
            print(f"[FALTA] {module_name} (instalar con: pip install {pip_name})")

if __name__ == "__main__":
    main()
