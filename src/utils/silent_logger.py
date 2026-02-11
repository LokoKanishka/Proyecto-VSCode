"""
Silent Progress Logger para arranque de Lucy.
Logging quirúrgico que solo muestra progreso esencial.
"""
import logging
import sys
from typing import Optional


class SilentProgressLogger:
    """Logger que solo muestra progreso crítico en terminal."""
    
    def __init__(self, total_steps: int, name: str = "lucy.swarm"):
        self.total_steps = total_steps
        self.current_step = 0
        self.file_logger = logging.getLogger(name)
        self._last_line_length = 0
        
    def step(self, component: str, status: str = "✅"):
        """Registra progreso de un componente."""
        self.current_step += 1
        
        # Terminal: solo una línea (overwrite)
        message = f"⚡ [{self.current_step}/{self.total_steps}] {component}... {status}"
        sys.stdout.write(f"\r{message}")
        sys.stdout.flush()
        self._last_line_length = len(message)
        
        # Archivo: log completo
        self.file_logger.info(f"Component {component}: {status}")
    
    def finish(self, final_message: str = "✅ Sistema listo"):
        """Finaliza el progreso con mensaje."""
        # Limpiar línea anterior
        sys.stdout.write("\r" + " " * self._last_line_length + "\r")
        sys.stdout.write(f"{final_message}\n")
        sys.stdout.flush()
    
    def error(self, message: str):
        """Muestra error."""
        sys.stdout.write("\r" + " " * self._last_line_length + "\r")
        sys.stdout.write(f"❌ {message}\n")
        sys.stdout.flush()
        self.file_logger.error(message)


def setup_silent_logging(level: int = logging.INFO) -> logging.Logger:
    """Configura logging silencioso para Lucy."""
    logger = logging.getLogger("lucy")
    logger.setLevel(level)
    
    # Solo log a archivo, no a terminal
    from pathlib import Path
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    file_handler = logging.FileHandler(log_dir / "swarm.log")
    file_handler.setLevel(level)
    formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    file_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    
    # NO agregar StreamHandler para evitar ruido en terminal
    return logger
