#!/usr/bin/env python3
"""
test_lucy_tools_screenshot.py – Prueba de la función `tomar_captura` de LucyTools.

Objetivo:
    - Verificar que `lucy_tools.tomar_captura` crea un archivo PNG
      en el directorio de tests sin efectos secundarios peligrosos.
"""

from pathlib import Path

from lucy_voice import lucy_tools


def main():
    print("== Prueba de LucyTools: captura de pantalla ==")
    ruta = lucy_tools.tomar_captura("lucy_tools_screenshot.png")
    print(f"[OK] Captura generada en: {ruta}")

    if not Path(ruta).exists():
        print("[ERROR] La ruta devuelta no existe en disco.")
    else:
        print("[OK] Archivo encontrado en disco.")


if __name__ == "__main__":
    main()
