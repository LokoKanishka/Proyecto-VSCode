#!/usr/bin/env python3
"""
test_pipecat_import.py – Prueba mínima de que Pipecat está instalado y accesible
dentro del entorno de voz de Lucy.
"""

import pipecat


def main():
    version = getattr(pipecat, "__version__", "desconocida")
    print("== Prueba mínima de Pipecat ==")
    print(f"Pipecat importado correctamente. Versión: {version}")


if __name__ == "__main__":
    main()
