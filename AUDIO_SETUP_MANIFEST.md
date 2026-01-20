# 📦 MANIFIESTO DE INSTALACIÓN (Módulo de Audio - Máquina Géminis)
# Usar este archivo para replicar el entorno de voz en la Máquina ChatGPT.

## 1. Dependencias del Sistema (Linux/Ubuntu/WSL)
# Necesarias para compilar PyAudio y manejar audio.
sudo apt update
sudo apt install -y python3-dev python3-pip python3-venv \
    portaudio19-dev libasound2-dev libespeak-ng1 libsndfile1 ffmpeg

## 2. Modelos de Ollama (Cerebro Local)
# Instalar Ollama desde https://ollama.com/
ollama pull tinyllama  # Para pruebas ultrarrápidas
ollama pull phi3       # Para conversación ligera
# ollama pull llama3   # (Opcional si la máquina tiene GPU grande)

## 3. Instalación de Mimic3 (Motor de Voz TTS)
# Mimic3 requiere un repo específico o instalación vía pip con flags extra.
pip install mycroft-mimic3-tts

# Descargar voz en español (se hace automático al primer uso, pero para pre-cargar):
mimic3 --voice es_ES/m-ailabs_low#karen_savage --preload-voice

## 4. Dependencias de Python (requirements.txt)
# Copiar este bloque en un archivo requirements_audio.txt e instalar con:
# pip install -r requirements_audio.txt

customtkinter      # Interfaz Gráfica
faster-whisper     # Reconocimiento de voz (STT) optimizado
sounddevice        # Grabación de audio
scipy              # Guardado de archivos WAV
numpy              # Manejo de arrays de audio
requests           # Conexión con Ollama
pyttsx3            # (Opcional: TTS de respaldo)

## 5. Configuración de Variables (Solo si usas WSL)
# Si la máquina ChatGPT es Windows/WSL, recuerda el puente de audio:
# export PULSE_SERVER=unix:/mnt/wslg/PulseServer
