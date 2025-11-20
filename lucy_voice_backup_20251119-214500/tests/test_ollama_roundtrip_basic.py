import pytest

from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline, LucyPipelineConfig


@pytest.mark.slow
def test_ollama_roundtrip_basico():
    """Smoke test muy simple para el pipeline texto→LLM.

    No valida el contenido, sólo que:
      - Se puede instanciar el pipeline
      - Llamar a run_text_roundtrip() no revienta
      - Devuelve un string no vacío

    Si Ollama no está instalado o el modelo no existe, el pipeline devuelve
    un mensaje de error legible, pero el test igualmente pasa (es un test
    de estabilidad, no de entorno).
    """
    cfg = LucyPipelineConfig()
    pipeline = LucyVoicePipeline(cfg)

    respuesta = pipeline.run_text_roundtrip(
        "Decime una frase muy corta para probar que estás viva."
    )

    assert isinstance(respuesta, str)
    assert respuesta.strip()
