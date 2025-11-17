"""
voice_chat_loop.py

Modo conversación por voz con Lucy:

- Inicializa LucyVoicePipeline.
- Construye el grafo (stub actual de Pipecat).
- Entra en un bucle donde cada iteración hace:
    micrófono → ASR → LLM → TTS.

Para salir, usar Ctrl+C en la terminal.
"""

from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline


def main() -> None:
    pipeline = LucyVoicePipeline()
    pipeline.build_graph()

    print("Lucy voz (modo VOZ).")
    print("Voy a escuchar, pensar y responder en voz.")
    print("Usá Ctrl+C en la terminal para terminar.\n")

    try:
        while True:
            # Una vuelta completa: mic → ASR → LLM → TTS
            pipeline.run_mic_llm_roundtrip_once(duration_sec=5.0)
    except KeyboardInterrupt:
        print("\n[LucyVoiceVoiceChat] Fin de la sesión de voz. Chau 💜")


if __name__ == "__main__":
    main()
