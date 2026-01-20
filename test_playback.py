import subprocess
import os
import time

print("\n🔊 --- DIAGNÓSTICO DE SALIDA DE AUDIO ---")
print("Voy a intentar reproducir un sonido de prueba.")
print("Asegúrate de tener el volumen de Windows y WSL al máximo.")

# 1. Crear un audio de prueba si no existe
test_wav = "test_output.wav"
if not os.path.exists(test_wav):
    print("Generando audio de prueba con Mimic3...")
    subprocess.run(["mimic3", "Probando salida de audio. Uno, dos, tres."], stdout=open(test_wav, "wb"))

# 2. Intentar reproducir con diferentes reproductores
players = ["paplay", "aplay", "pw-play"]

for player in players:
    print(f"\nIntentando con: {player}...")
    try:
        result = subprocess.run([player, test_wav], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {player} ejecutado sin errores. ¿Escuchaste algo?")
        else:
            print(f"❌ {player} falló: {result.stderr}")
    except FileNotFoundError:
        print(f"⚠️ {player} no está instalado.")

print("\n--- FIN DEL DIAGNÓSTICO ---")
print("Si no escuchaste nada, revisa pavucontrol o la configuración de audio de Windows.")
