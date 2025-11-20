from pathlib import Path
import numpy as np
from openwakeword.model import Model


def main():
    print("== Prueba básica de OpenWakeWord ==")

    # 1. Crear modelo con la configuración por defecto
    print("[INFO] Creando modelo por defecto...")
    model = Model()

    # 2. Crear un frame de 'silencio' (16 kHz, 0.5 segundos)
    sr = 16000
    frame = np.zeros(int(sr * 0.5), dtype=np.int16)

    # 3. Obtener predicciones para ese frame
    print("[INFO] Ejecutando predicción sobre silencio...")
    prediction = model.predict(frame)

    print("\nModelos cargados y puntuaciones:")
    for name, score in prediction.items():
        print(f"- {name}: {score:.4f}")

    print("\nSi llegaste hasta acá sin errores, OpenWakeWord está instalado y funcionando.")


if __name__ == "__main__":
    main()
