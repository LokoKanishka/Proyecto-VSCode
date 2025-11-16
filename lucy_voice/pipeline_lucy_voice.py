"""
Lucy voz – Fase 2: pipeline base con Pipecat y LLM local.

Por ahora este módulo define:
- La estructura vacía del pipeline (pensado para Pipecat más adelante).
- Un camino simple de texto: recibe una frase, la pasa a un LLM local (Ollama)
  y devuelve la respuesta, sin audio todavía.
- Un modo chat interactivo en consola para probar el "cerebro" de Lucy.

Así podemos probar cómo piensa Lucy antes de encastrar micrófono, ASR y TTS.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import subprocess
import textwrap

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

    En esta etapa de Fase 2:
    - Tenemos un camino de texto → LLM → texto (sin audio).
    - Y un modo chat en consola para probar el "cerebro" de Lucy.
    """

    def __init__(self, config: Optional[LucyPipelineConfig] = None) -> None:
        self.config = config or LucyPipelineConfig()
        self._graph: Any = None  # Acá va a ir el grafo de Pipecat cuando lo implementemos.

    # -------------------------------------------------------------------------
    # Bloque futuro: grafo de Pipecat
    # -------------------------------------------------------------------------
    def build_graph(self) -> None:
        """
        Construye el grafo de Pipecat.

        Por ahora solo deja marcados los "lugares" donde irán los nodos reales.
        """
        self._graph = "PENDING_IMPLEMENTATION"
        print("[LucyVoicePipeline] build_graph(): grafo aún no implementado (solo marcador).")

    def start(self) -> None:
        """
        Punto de entrada para arrancar el pipeline "real" (cuando exista el grafo).
        """
        if self._graph is None:
            print("[LucyVoicePipeline] start(): no hay grafo definido todavía.")
            return

        if self._graph == "PENDING_IMPLEMENTATION":
            print("[LucyVoicePipeline] start(): el grafo está marcado como PENDING_IMPLEMENTATION.")
            return

        print("[LucyVoicePipeline] start(): pipeline real aún no está implementado.")

    def stop(self) -> None:
        """
        Detiene el pipeline y libera recursos.
        """
        print("[LucyVoicePipeline] stop(): nada que detener todavía (esqueleto).")

    # -------------------------------------------------------------------------
    # Bloque actual: camino simple de texto → LLM → texto (sin audio)
    # -------------------------------------------------------------------------
    def _query_llm_with_ollama(self, prompt: str) -> str:
        """
        Llama al modelo local en Ollama usando la CLI.

        Usa el modelo configurado en self.config.llm_model (por defecto gpt-oss:20b).
        """
        model = self.config.llm_model
        cmd = ["ollama", "run", model, prompt]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
        except FileNotFoundError:
            raise RuntimeError(
                "No se encontró el comando 'ollama'. "
                "Asegurate de que Ollama está instalado y en el PATH."
            ) from None
        except subprocess.CalledProcessError as e:
            raise RuntimeError(
                f"Error al ejecutar ollama con el modelo {model}: {e.stderr.strip()}"
            ) from None

        return result.stdout.strip()

    def run_text_roundtrip(self, user_text: str) -> str:
        """
        Ejecuta un "roundtrip" simple: texto de usuario → LLM local → texto de respuesta.
        """
        system_prompt = (
            "Actuá como Lucy, un asistente de voz local que corre en una PC con Linux. "
            "Respondé en castellano rioplatense, en una o pocas frases claras, "
            "sin enumeraciones largas ni formato raro."
        )

        prompt = textwrap.dedent(
            f"""\
            {system_prompt}

            Usuario: {user_text}
            Lucy:"""
        )

        answer = self._query_llm_with_ollama(prompt)

        print("[LucyVoicePipeline] Usuario:", user_text)
        print("[LucyVoicePipeline] Lucy:", answer)

        return answer

    # -------------------------------------------------------------------------
    # Modo chat interactivo en consola
    # -------------------------------------------------------------------------
    def interactive_loop(self) -> None:
        """
        Bucle simple de chat en consola con Lucy usando el LLM local.

        Esto es útil como "simulador" del pipeline antes de conectar audio real.
        """
        print("Lucy voz (modo texto). Escribí 'salir' para terminar.\n")

        while True:
            try:
                user = input("Vos: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n[LucyVoicePipeline] Fin de la sesión.")
                break

            if user.lower() in {"salir", "exit", "quit"}:
                print("[LucyVoicePipeline] Chau, hasta luego 💜")
                break

            if not user:
                continue

            try:
                self.run_text_roundtrip(user)
            except RuntimeError as e:
                print(f"[LucyVoicePipeline] Error: {e}")
                break


def main() -> None:
    """
    Punto de entrada para pruebas manuales.

    Permite ejecutar:

        python -m lucy_voice.pipeline_lucy_voice

    para:
    - comprobar que pipecat se importa bien, y
    - chatear con Lucy en modo texto usando el LLM local.
    """
    pipeline = LucyVoicePipeline()
    pipeline.build_graph()  # deja el marcador de grafo pendiente
    pipeline.interactive_loop()


if __name__ == "__main__":
    main()
