import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import time
import os
from faster_whisper import WhisperModel

# CONFIGURACIÓN DE PRUEBA
SAMPLE_RATE = 16000
DURATION = 5  # Segundos
OUTPUT_WAV = "test_debug.wav"

def color_print(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")

def run_diagnostic():
    # os.system('clear') # Avoiding clear in automated environment
    print("🕵️‍♂️ --- ANTIGRAVITY AUDIO MONITOR ---")
    print("1. Verificando Hardware de Audio...")
    
    try:
        # Info del dispositivo
        device_info = sd.query_devices(kind='input')
        print(f"   🎤 Micrófono detectado: {device_info['name']}")
    except Exception as e:
        color_print(f"   ⚠️ Info del dispositivo no disponible directamente: {e}", "33")

    print("\n2. Cargando Modelo Ligero (BASE) para prueba de CPU...")
    t0 = time.time()
    try:
        # Usamos 'base' para descartar que sea problema de potencia
        model = WhisperModel("base", device="cpu", compute_type="int8")
        load_time = time.time() - t0
        color_print(f"✅ Modelo cargado en {load_time:.2f} segundos.", "32")
    except Exception as e:
        color_print(f"❌ ERROR CARGANDO WHISPER: {e}", "31")
        return

    print(f"\n3. 🔴 GRABANDO {DURATION} SEGUNDOS...")
    print("   Hable claro y fuerte: 'Hola Lucy, esto es una prueba de diagnóstico'.")
    
    try:
        audio = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
        
        # Barra de progreso visual mientras graba
        for i in range(DURATION):
            time.sleep(1)
            print(f"   ⏱️ {i+1}/{DURATION}...", end="\r", flush=True)
        sd.wait()
        print("\n   ⏹️ Grabación finalizada.")
        
        # Guardar para verificación humana
        audio_int16 = (audio * 32767).astype(np.int16)
        wav.write(OUTPUT_WAV, SAMPLE_RATE, audio_int16)
        print(f"   💾 Audio guardado en '{OUTPUT_WAV}'.")
        
        # Análisis de señal
        max_amp = np.max(np.abs(audio))
        print(f"   📊 Nivel Máximo de Señal: {max_amp:.4f}")
        
        if max_amp < 0.01:
            color_print("⚠️ ALERTA: Volumen MUY BAJO o SILENCIO. ¿El micrófono está muteado?", "33")
        elif max_amp > 0.95:
            color_print("⚠️ ALERTA: Audio SATURADO (Clipping). Aléjate del micro.", "33")
        else:
            color_print("✅ Nivel de audio saludable.", "32")

    except Exception as e:
        color_print(f"❌ ERROR GRABANDO: {e}", "31")
        return

    print("\n4. 🧠 Transcribiendo...")
    t_start = time.time()
    try:
        segments, info = model.transcribe(audio.flatten(), beam_size=5, language="es")
        text = " ".join([segment.text for segment in segments]).strip()
        t_end = time.time()
        
        process_time = t_end - t_start
        
        print("\n" + "="*40)
        print(f"⏱️ TIEMPO DE PROCESAMIENTO: {process_time:.2f} segundos")
        print("="*40)
        
        if text:
            color_print(f"📝 TRANSCRIPCIÓN: '{text}'", "36") # Cyan
        else:
            color_print("❌ TRANSCRIPCIÓN VACÍA (El modelo escuchó silencio)", "31")

        if process_time > 5.0:
            color_print("⚠️ ADVERTENCIA: La CPU está sufriendo. Latencia alta.", "33")

    except Exception as e:
        color_print(f"❌ ERROR TRANSCRIBIENDO: {e}", "31")

if __name__ == "__main__":
    run_diagnostic()
