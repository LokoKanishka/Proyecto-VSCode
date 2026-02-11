import sys
import os
import time

# Asegurar que el motor sea importable
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path: sys.path.append(project_root)

from src.engine.voice_bridge import LucyVoiceBridge

def test_voice_system():
    print("🎙️ --- INICIANDO DIAGNÓSTICO INTEGRAL DE VOZ V3.2 ---")
    print("Este test probará el Oído Biónico y la Interrupción de Voz.")
    
    bridge = LucyVoiceBridge()
    
    if not bridge.asr_model or not bridge.vad_model:
        print("❌ Error: No se pudieron cargar los modelos de voz/VAD.")
        return

    print("\n--- PASO 1: Prueba de Habla e Interrupción ---")
    print("Lucy va a hablar. Intenta interrumpirla hablando fuerte.")
    test_text = (
        "Hola Xdie, estoy probando el sistema de interrupción de voz. "
        "Si me escuchas y me hablas encima, debería callarme de inmediato. "
        "Esta es una frase larga diseñada específicamente para darte tiempo a interrumpirme "
        "y verificar que el motor de audio está funcionando en modo Full-Duplex."
    )
    bridge.say(test_text)
    
    print("\n--- PASO 2: Prueba de Oído Biónico (VAD) ---")
    print("Dí algo ahora (como 'Hola Lucy, ¿me escuchas?')")
    print("El sistema detectará automáticamente cuando termines de hablar.")
    
    transcription = bridge.listen_continuous()
    
    if transcription:
        print(f"\n📝 [ÉXITO] Transcripción detectada: '{transcription}'")
        bridge.say(f"Te escuché perfectamente. Dijiste: {transcription}")
    else:
        print("\n⚠️ No se detectó ninguna transcripción clara.")

    print("\n--- DIAGNÓSTICO FINALIZADO ---")

if __name__ == "__main__":
    test_voice_system()
