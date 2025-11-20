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

from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline


def main() -> None:
    pipeline = LucyVoicePipeline()
    pipeline.build_graph()

    print("Lucy voz (modo VOZ).")
    print("Cada turno:")
    print("  - Apretá Enter solo para grabar")
    print("  - Escribí 'salir' y Enter para terminar\n")

    try:
        while True:
            comando = input("[Enter=hablar | 'salir'=terminar]: ").strip().lower()

            if comando in {"salir", "exit", "quit"}:
                print("[LucyVoiceVoiceChat] Fin de la sesión de voz. Chau 💜")
                break

            # Si sólo apretaste Enter (comando vacío), grabamos un turno de voz
            print()
            should_stop = pipeline.run_mic_llm_roundtrip_once(duration_sec=5.0)
            print()

            if should_stop:
                print("[LucyVoiceVoiceChat] Desactivada por comando de voz. Chau 💜")
                break
    except KeyboardInterrupt:
        print("\n[LucyVoiceVoiceChat] Sesión interrumpida. Chau 💜")


if __name__ == "__main__":
    main()
