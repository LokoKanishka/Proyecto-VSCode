import sounddevice as sd
import numpy as np
import wave
import os
import sys

# Configuración
DURATION = 5  # Segundos
FS = 16000    # Frecuencia estándar
CHANNELS = 1

print("\n🎤 --- DIAGNÓSTICO DE AUDIO RAW ---")
print("Voy a grabar 5 segundos DIRECTOS del micrófono.")
print("Di fuerte y claro: 'HOLA LUCY, ESTO ES UNA PRUEBA'.")
print("3...")
time.sleep(1)
print("2...")
time.sleep(1)
print("1...")
time.sleep(1)
print("🔴 ¡HABLA AHORA!")

try:
    # Grabar sin ningún efecto ni ganancia extra
    recording = sd.rec(int(DURATION * FS), samplerate=FS, channels=CHANNELS, dtype='int16')
    sd.wait()
    print("✅ Grabación finalizada.")

    # Ruta para guardar en Windows (Acceso Público para que lo encuentres fácil)
    win_path = "/mnt/c/Users/Public/prueba_audio.wav"

    # Guardar archivo WAV
    with wave.open(win_path, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(2) # 16 bit
        wf.setframerate(FS)
        wf.writeframes(recording.tobytes())
        
    print(f"\n💾 --- ÉXITO ---")
    print(r"El archivo se guardó en: C:\Users\Public\prueba_audio.wav")
    print(f"👉 Ve a Windows, abre esa carpeta y ESCÚCHALO.")

except Exception as e:
    print(f"\n❌ Error: {e}")
    print("Asegúrate de tener un micrófono configurado en 'pavucontrol'.")

