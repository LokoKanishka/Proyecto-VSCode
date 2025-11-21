"""
voice_chat_loop.py

Modo conversación por voz con Lucy (push-to-talk):

- Inicializa LucyVoicePipeline.
- Construye el grafo (stub actual de Pipecat).
- Entra en un bucle donde CADA TURNO lo disparás vos:
    - Apretás Enter para grabar unos segundos.
    - Lucy transcribe, piensa y responde en voz.
    - Escribís 'salir' para terminar.

Mientras no toques nada, NO graba.
"""

from lucy_voice.config import LucyConfig
from lucy_voice.pipeline.voice_pipeline import LucyOrchestrator

def main():
    config = LucyConfig()
    # Use the orchestrator for PTT mode (legacy/simple mode)
    orchestrator = LucyOrchestrator(config)

    print("Lucy voz (modo VOZ).")
    print("Cada turno:")
    print("  - Apretá Enter solo para grabar")
    print("  - Escribí 'salir' y Enter para terminar")
    ...


    try:
        while True:
            comando = input("[Enter=hablar | 'salir'=terminar]: ").strip().lower()

            if comando in {"salir", "exit", "quit"}:
                print("[LucyVoiceVoiceChat] Fin de la sesión de voz. Chau 💜")
                break

            # Si sólo apretaste Enter (comando vacío), grabamos un turno de voz
            print()
            # Orchestrator roundtrip
            should_stop = orchestrator.run_turn()
            print()

            if should_stop:
                print("[LucyVoiceVoiceChat] Desactivada por comando de voz. Chau 💜")
                break
    except KeyboardInterrupt:
        print("\n[LucyVoiceVoiceChat] Sesión interrumpida. Chau 💜")


if __name__ == "__main__":
    main()
