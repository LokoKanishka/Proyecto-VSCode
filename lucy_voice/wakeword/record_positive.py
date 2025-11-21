import os
import sys
import time
import queue
import pathlib
import datetime as dt

import sounddevice as sd
import soundfile as sf  # también open-source, liviano

from lucy_voice.config import LucyConfig

# Parámetros básicos
config = LucyConfig()
SAMPLE_RATE = config.sample_rate
CHANNELS = config.channels
DURATION_SEC = 1.5

POS_DIR = config.base_dir / "lucy_voice" / "data" / "wakeword" / "hola_lucy" / "positive"

def record_one_sample(index: int):
    """Graba un clip corto de 'hola Lucy' y lo guarda como WAV."""
    POS_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = POS_DIR / f"hola_lucy_{index:03d}_{ts}.wav"

    print(f"\n[Grabación] Preparáte para decir: 'hola Lucy'")
    time.sleep(0.5)
    print(f"[Grabación] Grabando {DURATION_SEC} s...")

    audio = sd.rec(
        int(DURATION_SEC * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()

    # Guardar en WAV mono, 16 kHz
    sf.write(str(filename), audio, SAMPLE_RATE)
    print(f"[Grabación] Guardado en: {filename}")

def main():
    print("=== Grabador de wake word: 'hola Lucy' ===")
    print("Este script guarda muestras POSITIVAS en:")
    print(f"  {POS_DIR}")
    print("\nInstrucciones:")
    print("  - Cada vez que presiones Enter, graba 1.5 s.")
    print("  - En ese tiempo, decí claramente: 'hola Lucy'.")
    print("  - Escribí 'q' y Enter para salir.\n")

    idx = 1
    while True:
        user_input = input(f"[Grabador] Enter = grabar muestra #{idx}, 'q' = salir: ").strip().lower()
        if user_input == "q":
            print("[Grabador] Saliendo. Chau 💜")
            break

        try:
            record_one_sample(idx)
            idx += 1
        except KeyboardInterrupt:
            print("\n[Grabador] Interrumpido por teclado. Saliendo.")
            break
        except Exception as e:
            print(f"[Error] Ocurrió un problema al grabar: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
