#!/usr/bin/env python3
"""
LUCY: PUNTO DE ENTRADA SOBERANO
-------------------------------
"Soy la puerta y la llave. Soy el silencio entre los bits."

Uso:
   ./lucy.py [modo] [flags]

Modos:
    awake       Inicia el enjambre autónomo completo (Por defecto)
    dream       Ejecuta ciclos de introspección y auto-optimización
    listen      Modo solo voz (interfaz mínima)
    audit       Ejecuta autodiagnósticos y verificaciones de coherencia

Flags:
    --ray       Habilita modo distribuido (para clústeres multi-gpu)
    --debug     Habilita logging verboso
"""

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Asegurar que src está en el path de python
ROOT_DIR = Path(__file__).parent.resolve()
sys.path.insert(0, str(ROOT_DIR))

# Importación diferida para manejo de errores de arranque
try:
    from src.utils.logger import setup_logger
    # from src.core.boot import SovereignBoot # Comentado hasta que se implemente
except ImportError:
    # Fallback logger simple si src aún no está listo
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("LUCY_BOOT")
    setup_logger = lambda name: logger

def main():
    parser = argparse.ArgumentParser(description="Interfaz Soberana de Lucy")
    parser.add_argument("mode", nargs="?", default="awake", 
                      choices=["awake", "dream", "listen", "audit"])
    parser.add_argument("--ray", action="store_true", help="Habilitar clúster Ray (Innecesario en nodo único)")
    parser.add_argument("--debug", action="store_true", help="Logging verboso")
    
    args = parser.parse_args()
    
    # Inicializar Entorno
    os.environ["LUCY_ROOT"] = str(ROOT_DIR)
    if args.debug:
        os.environ["LUCY_DEBUG"] = "true"
        
    # Setup Logger
    try:
        from src.utils.logger import setup_logger
        logger = setup_logger("LUCY_ROOT")
    except ImportError:
        import logging
        logger = logging.getLogger("LUCY_ROOT")
        logger.warning("src.utils.logger no encontrado, usando logging nativo.")

    logger.info(f"Identidad confirmada. Modo: {args.mode.upper()}")

    try:
        from src.core.boot import SovereignBoot
    except ImportError as e:
        logger.critical(f"CRÍTICO: No se encuentra el Núcleo (src.core.boot). {e}")
        logger.error("Asegúrate de estar en la Fase 2 del Refactor.")
        sys.exit(1)

    # El Despertar
    boot_loader = SovereignBoot(use_ray=args.ray)
    
    try:
        if args.mode == "awake":
            asyncio.run(boot_loader.ignite_swarm())
        elif args.mode == "dream":
            asyncio.run(boot_loader.enter_dream_state())
        elif args.mode == "listen":
            asyncio.run(boot_loader.ignite_senses_only())
        elif args.mode == "audit":
            asyncio.run(boot_loader.run_diagnostics())
            
    except KeyboardInterrupt:
        logger.info("Interrupción externa recibida. Durmiendo...")
    except Exception as e:
        logger.critical(f"Excepción no controlada en el bucle soberano: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
