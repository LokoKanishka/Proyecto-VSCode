import sounddevice as sd
import numpy as np
import time

print("=== 🔍 LISTA DE DISPOSITIVOS ===")
print(sd.query_devices())
print("================================")

print("\n🎤 PRUEBA DE GRABACIÓN (3 segundos)...")
print("--> ¡HABLA ALTO AHORA! <--")

try:
    duration = 3  # segundos
    fs = 16000
    # Grabar
    myrecording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    
    # Calcular volumen
    volume = np.linalg.norm(myrecording) * 10
    print(f"\n📊 Nivel de volumen detectado: {volume:.4f}")
    
    if volume < 1.0:
        print("❌ ERROR: El volumen es demasiado bajo (casi silencio).")
        print("   Posible causa: Dispositivo incorrecto o micrófono muteado.")
    else:
        print("✅ ÉXITO: Se detectó audio correctamente.")
        print("🔊 Reproduciendo lo grabado para confirmar...")
        sd.play(myrecording, fs)
        sd.wait()
        print("¿Te escuchaste?")

except Exception as e:
    print(f"❌ ERROR CRÍTICO: {e}")
