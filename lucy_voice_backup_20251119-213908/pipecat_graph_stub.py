"""
pipecat_graph_stub.py

Stub inicial para el grafo de Pipecat de Lucy.
Por ahora **no** procesa audio ni texto: sólo comprueba que podemos
importar las piezas básicas que vamos a usar en la Fase 3.
"""

from loguru import logger

# Piezas básicas de Pipecat que vamos a necesitar más adelante
from pipecat.pipeline.pipeline import Pipeline

def main() -> None:
    """
    Entrada mínima de prueba.

    Crea un Pipeline vacío sólo para verificar que la clase se puede
    importar y construir sin errores en este entorno.
    """
    logger.info("[LucyPipecatStub] Import de Pipeline OK, creando pipeline vacío…")

    # Más adelante vamos a pasarle la lista de procesadores (STT, LLM, TTS, etc.).
    pipeline = Pipeline([])

    logger.info("[LucyPipecatStub] Pipeline creado correctamente: %r", pipeline)
    logger.info("[LucyPipecatStub] Stub listo. En próximos pasos vamos a llenar este pipeline.")

if __name__ == "__main__":
    main()

def build_lucy_pipeline() -> Pipeline:
    """
    Fábrica mínima del Pipeline de Lucy.

    Hoy devuelve un Pipeline vacío; en los próximos pasos vamos a ir
    agregando procesadores (STT, LLM, TTS, etc.) dentro de esta función.
    """
    logger.info("[LucyPipecatStub] build_lucy_pipeline(): creando pipeline vacío…")

    # Por ahora usamos un pipeline vacío. Más adelante vamos a ir
    # reemplazando esta lista por los procesadores reales.
    pipeline = Pipeline([])

    logger.info("[LucyPipecatStub] build_lucy_pipeline(): pipeline creado: %r", pipeline)
    return pipeline
