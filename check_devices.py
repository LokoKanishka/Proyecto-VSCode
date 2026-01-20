import sounddevice as sd

print("\n🎧 --- AUDITORÍA DE DISPOSITIVOS DE AUDIO (WSL) ---")
print(f"Sistema de Audio Host: {sd.get_portaudio_version()[1]}")

devices = sd.query_devices()
try:
    default_input = sd.default.device[0]
except:
    default_input = -1

print(f"\n🔍 Dispositivo por defecto actual: ID {default_input}")
print("-" * 60)
print(f"{'ID':<4} {'NOMBRE':<40} {'CANALES':<10} {'TIPO'}")
print("-" * 60)

for i, dev in enumerate(devices):
    mark = "⭐" if i == default_input else "  "
    kind = "ENTRADA" if dev['max_input_channels'] > 0 else "SALIDA"
    if dev['max_input_channels'] > 0:
        print(f"{mark} {i:<3} {dev['name'][:38]:<40} {dev['max_input_channels']:<10} {kind}")

print("-" * 60)
print("NOTA: Si ves muchos 'dmix' o 'snooper', son virtuales.")
print("Buscamos algo como 'PulseAudio', 'default', o 'HDA Intel'.\n")
