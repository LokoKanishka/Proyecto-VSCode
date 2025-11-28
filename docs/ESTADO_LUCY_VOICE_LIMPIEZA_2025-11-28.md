# Estado de limpieza Lucy Voice - 2025-11-28

- Eliminé archivos de prueba grandes: lucy_voice_complete.zip, lucy_voice_refactored.zip, lucy_tts_output.wav, mic_test.wav, test_output.txt, codigo_fuente.txt y pregunta_para_chatgpt.txt.
- Actualicé .gitignore para ignorar entornos virtuales (.venv*/venv*), bytecode de Python, audios .wav, zips y temporales.
- Ejecuté `python3 -m compileall lucy_voice` y quedó sin errores tras corregir la indentación en `lucy_voice/pipeline_lucy_voice.py`.
- No toqué scripts ni otros docs; solo limpieza y verificación rápida.
