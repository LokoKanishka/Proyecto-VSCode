import subprocess
import os
import time

print("\n🔊 --- DIAGNÓSTICO DE SALIDA DE AUDIO ---")
print("Voy a intentar reproducir un sonido de prueba.")
print("Asegúrate de tener el volumen de Windows y WSL al máximo.")

# Intentar encontrar mimic3
mimic3_paths = [
    "mimic3",
    "/home/xdie/Proyecto-VSCode/.venv/bin/mimic3",
    "/home/xdie/Proyecto-VSCode/scripts/bin/mimic3",
    os.path.expanduser("~/.local/bin/mimic3")
]

mimic_bin = "mimic3"
for p in mimic3_paths:
    if os.path.exists(p) or subprocess.run(["which", p], capture_output=True).returncode == 0:
        mimic_bin = p
        break

# 1. Crear un audio de prueba si no existe
test_wav = "test_output.wav"
if not os.path.exists(test_wav):
    print(f"Generando audio de prueba con {mimic_bin}...")
    try:
        subprocess.run([mimic_bin, "Probando salida de audio. Uno, dos, tres."], stdout=open(test_wav, "wb"))
    except Exception as e:
        print(f"❌ Error generando audio: {e}")
        # Intentar crear un wav vacío o de ruido si mimic falla para probar los reproductores
        print("Intentando generar un archivo de prueba alternativo...")
        subprocess.run(["sox", "-n", "-r", "16000", "-c", "1", test_wav, "trim", "0", "2"])

# 2. Intentar reproducir con diferentes reproductores
players = ["paplay", "aplay", "pw-play"]

if os.path.exists(test_wav):
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
else:
    print("❌ No se pudo crear el archivo de audio de prueba.")

print("\n--- FIN DEL DIAGNÓSTICO ---")
