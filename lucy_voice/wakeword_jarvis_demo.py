import sys
import time

import numpy as np
import sounddevice as sd
from openwakeword import Model

SAMPLE_RATE = 16000
BLOCKSIZE = 1280  # ~80 ms a 16 kHz
THRESHOLD = 0.15  # <-- umbral más bajo (antes era 0.3)


def main():
    print("[WakeWordDemo] Cargando modelos de wake word (esto puede tardar unos segundos)...")
    model = Model()  # carga todos los modelos incluidos en openwakeword

    print("")
    print("=== Demo wake word (probando modelos incluidos) ===")
    print("Decí varias veces: 'hey jarvis' o 'alexa' cerca del micrófono, pero en voz NORMAL.")
    print("Vas a ver el puntaje subiendo; si pasa el umbral, se avisa.")
    print("Para salir, usá Ctrl+C en la terminal.")
    print("")

    detected_key = None
    printed_keys = False

    try:
        with sd.InputStream(
            channels=1,
            samplerate=SAMPLE_RATE,
            blocksize=BLOCKSIZE,
            dtype="float32",
        ) as stream:
            while True:
                audio, _ = stream.read(BLOCKSIZE)
                # audio viene como float32 en [-1, 1]; openwakeword espera int16 (16-bit PCM)
                mono = audio[:, 0].astype(np.float32)
                mono_int16 = (mono * 32767).astype(np.int16)

                prediction = model.predict(mono_int16)

                # La primera vez, mostramos todas las claves que devuelve predict()
                if not printed_keys:
                    print("\n[WakeWordDemo] Claves devueltas por predict():")
                    for k in prediction.keys():
                        print(" -", repr(k))
                    printed_keys = True

                # Detectar automáticamente qué modelo vamos a usar
                if detected_key is None and prediction:
                    if "hey jarvis" in prediction:
                        detected_key = "hey jarvis"
                    elif "hey_jarvis" in prediction:
                        detected_key = "hey_jarvis"
                    elif "alexa" in prediction:
                        detected_key = "alexa"
                    else:
                        # usar la primera clave que aparezca como demo
                        detected_key = next(iter(prediction.keys()))

                    print(f"\n[WakeWordDemo] Usando clave de modelo: {repr(detected_key)}")

                if not detected_key:
                    # Todavía no sabemos qué clave usar, seguimos leyendo
                    sys.stdout.write("\rEsperando claves válidas en prediction()...")
                    sys.stdout.flush()
                    time.sleep(0.1)
                    continue

                score = float(prediction.get(detected_key, 0.0))

                sys.stdout.write(f"\rScore {repr(detected_key)}: {score:0.3f}")
                sys.stdout.flush()

                if score >= THRESHOLD:
                    print(f"\n[WakeWordDemo] ¡Wake word detectado con score={score:0.3f}!")
                    time.sleep(1.0)

    except KeyboardInterrupt:
        print("\n[WakeWordDemo] Cortado por el usuario (Ctrl+C). Chau 💜")


if __name__ == "__main__":
    main()
