import sys
from loguru import logger

def setup_logger(name: str = "LUCY"):
    """
    Configura el logger con formato estándar.
    """
    # Remover handlers por defecto para evitar duplicados si se llama múltiples veces
    logger.remove()
    
    # Formato: TIEMPO | NIVEL | MODULO:LINEA | MENSAJE
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # Salida a stderr (consola)
    logger.add(sys.stderr, format=log_format, level="INFO")
    
    # Salida a archivo rotativo
    logger.add(
        "logs/lucy.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format=log_format
    )
    
    return logger

# Exponer el objeto logger configurado por defecto
default_logger = setup_logger()
