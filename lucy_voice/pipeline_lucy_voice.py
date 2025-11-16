"""
Lucy voz – Fase 2: pipeline base con Pipecat.

Por ahora este módulo solo define la estructura vacía del pipeline:
- NO conecta todavía micrófono, wake word, ASR, LLM ni TTS.
- Sirve como punto de entrada único para ir encastrando piezas de a poco.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

try:
    import pipecat  # noqa: F401  # Import placeholder, confirma que la librería existe
except ImportError:
    pipecat = None


@dataclass
class LucyPipelineConfig:
    """
    Configuración mínima del pipeline de Lucy voz.

    Más adelante acá vamos a ir agregando:
    - modelo ASR a usar,
    - modelo TTS,
    - modelo LLM en Ollama,
    - dispositivos de entrada/salida de audio, etc.
    """
    asr_model: str = "faster-whisper-small"
    tts_voice: str = "mimic3-es"  # placeholder
    llm_model: str = "gpt-oss:20b"  # modelo pesado por defecto (puede cambiarse luego)


class LucyVoicePipeline:
    """
    Orquestador de alto nivel del pipeline de Lucy.

    Responsabilidades generales (a futuro):
    - Construir el grafo de nodos (micrófono → wake word → VAD → ASR → LLM → TTS).
    - Manejar el estado (listening / thinking / speaking).
    - Exponer métodos start()/stop() para uso diario.
    """

    def __init__(self, config: Optional[LucyPipelineConfig] = None) -> None:
        self.config = config or LucyPipelineConfig()
        self._graph: Any = None  # Acá va a ir el grafo de Pipecat cuando lo implementemos.

    def build_graph(self) -> None:
        """
        Construye el grafo de Pipecat.

        Por ahora solo deja marcados los "lugares" donde irán los nodos reales.
        """
        # TODO:
        #  - crear nodo de micrófono / entrada de audio
        #  - crear nodo de wake word (OpenWakeWord)
        #  - crear nodo de VAD (detección de fin de frase)
        #  - crear nodo de ASR (faster-whisper)
        #  - crear nodo de LLM (Ollama, modelo self.config.llm_model)
        #  - crear nodo de TTS (Mimic 3 / XTTS-v2)
        #
        # Ejemplo a futuro (pseudo-código):
        #   mic = ...
        #   wake = ...
        #   vad = ...
        #   asr = ...
        #   llm = ...
        #   tts = ...
        #   self._graph = [mic, wake, vad, asr, llm, tts]
        #
        # De momento solo dejamos una marca visible:
        self._graph = "PENDING_IMPLEMENTATION"
        print("[LucyVoicePipeline] build_graph(): grafo aún no implementado.")

    def start(self) -> None:
        """
        Punto de entrada para arrancar el pipeline.

        Más adelante:
        - iniciará el loop de audio,
        - manejará half-duplex (no escuchar mientras habla),
        - y coordinará llamadas a herramientas (LucyTools).
        """
        if self._graph is None:
            raise RuntimeError(
                "Intentaste iniciar el pipeline sin haber llamado antes a build_graph()."
            )

        # TODO: implementar el loop de ejecución usando Pipecat.
        print("[LucyVoicePipeline] start(): pipeline aún no está implementado.")

    def stop(self) -> None:
        """
        Detiene el pipeline y libera recursos.

        Más adelante se encargará de:
        - cerrar streams de audio,
        - limpiar estados,
        - detener hilos/procesos si hiciera falta.
        """
        print("[LucyVoicePipeline] stop(): nada que detener todavía (esqueleto).")


def main() -> None:
    """
    Punto de entrada para pruebas manuales.

    Permite ejecutar:

        python -m lucy_voice.pipeline_lucy_voice

    para comprobar que el módulo se importa bien y que los métodos básicos existen.
    """
    pipeline = LucyVoicePipeline()
    pipeline.build_graph()
    pipeline.start()


if __name__ == "__main__":
    main()
