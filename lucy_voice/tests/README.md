# Pruebas de TTS de Lucy

Este directorio guarda archivos de prueba para el entorno de voz de Lucy.

- `lucy_tts_test.wav`: primera prueba de síntesis de voz local con Mimic 3
  usando la voz `es_ES/carlfm_low`.

Nota: en esta etapa todavía no se usa micrófono. El archivo es 100% síntesis,
sin sonido de ambiente.

## Prueba de ASR con faster-whisper

Script:
- `test_asr_from_tts.py`: usa el archivo `lucy_tts_test.wav` generado por Mimic 3
  y lo transcribe con `faster-whisper` (modelo `small`, en CPU).

En la primera prueba el modelo detectó correctamente el idioma español, aunque
la frase reconocida no coincidió exactamente con el texto original.
Esto se toma como prueba de funcionamiento del flujo WAV -> ASR, a refinar más adelante.

## Prueba de Pipecat

Script:
- `test_pipecat_import.py`: verifica que la librería `pipecat` se importa
  correctamente dentro del entorno virtual de Lucy-voz y muestra su versión.

Esta prueba confirma que el framework de orquestación que vamos a usar
para el pipeline de voz/agente está instalado y accesible.
