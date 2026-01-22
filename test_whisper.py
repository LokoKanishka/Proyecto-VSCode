from faster_whisper import WhisperModel
import os

print("⬇️ Cargando/Descargando modelo Whisper 'small'...")
# Esto forzará la descarga si no existe
model = WhisperModel("small", device="cpu", compute_type="int8")
print("✅ Modelo cargado.")

# Prueba de transcripción con un archivo dummy (o uno real si tienes)
print("🧠 Intentando transcribir...")
# Si no hay audio, solo probamos que el modelo cargue sin errores
print("Whisper está listo para usarse.")
