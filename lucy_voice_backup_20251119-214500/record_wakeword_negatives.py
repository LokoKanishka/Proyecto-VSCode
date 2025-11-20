import os
import sys
import time
import queue
import pathlib
import datetime as dt

import sounddevice as sd
import soundfile as sf  # mismo que usamos en el grabador positivo

# Parámetros básicos
SAMPLE_RATE = 16000
CHANNELS = 1
DURATION_SEC = 1.5  # duración de cada clip negativo

BASE_DIR = pathlib.Path(__file__).resolve().parent
NEG_DIR = BASE_DIR / "data" / "wakeword" / "hola_lucy" / "negative"

def record_one_sample(index: int, label: str = "neg"):
    """Graba un clip corto negativo (ruido, otras palabras) y lo guarda como WAV."""
    NEG_DIR.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = NEG_DIR / f"neg_{label}_{index:03d}_{ts}.wav"

    print(f"\n[Grabación NEG] Preparáte: va a grabar {DURATION_SEC} s.")
    time.sleep(0.5)
    print(f"[Grabación NEG] Grabando {DURATION_SEC} s...")

    audio = sd.rec(
        int(DURATION_SEC * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
    )
    sd.wait()

    # Guardar en WAV mono, 16 kHz
    sf.write(str(filename), audio, SAMPLE_RATE)
    print(f"[Grabación NEG] Guardado en: {filename}")

def main():
    print("=== Grabador de muestras NEGATIVAS para 'hola Lucy' ===")
    print("Este script guarda muestras NEGATIVAS en:")
    print(f"  {NEG_DIR}")
    print("\nInstrucciones:")
    print("  - Cada vez que presiones Enter, graba 1.5 s.")
    print("  - En ese tiempo NO digas 'hola Lucy'.")
    print("    Podés dejar solo ruido, hablar cualquier cosa, decir otros nombres, etc.")
    print("  - Opcional: antes de cada grabación podés escribir una etiqueta breve")
    print("    (ejemplo: 'ruido', 'charla', 'música') y Enter.")
    print("  - Escribí 'q' y Enter para salir.\n")

    idx = 1
    while True:
        label = input(f"[Grabador NEG] Etiqueta (o Enter para 'neg'), 'q' = salir: ").strip().lower()
        if label == "q":
            print("[Grabador NEG] Saliendo. Chau 💜")
            break
        if not label:
            label = "neg"

        try:
            record_one_sample(idx, label=label)
            idx += 1
        except KeyboardInterrupt:
            print("\n[Grabador NEG] Interrumpido por teclado. Saliendo.")
            break
        except Exception as e:
            print(f"[Error] Ocurrió un problema al grabar: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
