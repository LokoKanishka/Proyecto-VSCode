# ESTADO – Lucy Voz (Fase 2) – 20/11/2025

## Resumen rápido

En esta fecha, Lucy Voz tiene:

- **Modo voz push-to-talk estable**:
  - Comando: `python -m lucy_voice.voice_chat_loop`
  - Lucy escucha cuando apretás **Enter**, responde por voz y vuelve a esperar.
- **Salida limpia del LLM**:
  - Lucy ya no lee en voz partes tipo “Thinking…” ni explicaciones internas.
  - Solo habla la frase final en castellano (“sí, ¿en qué te puedo ayudar?”, etc.).
- **Half-duplex práctico**:
  - Mientras habla, Lucy **no escucha**.
  - Cuando termina de hablar, vuelve a mostrar `[Enter=hablar | 'salir'=terminar]:`
  - Esto evita que se pisen tu voz y la de Lucy.

Todo corre 100% local sobre Ubuntu, usando Ollama + gpt-oss:20b, faster-whisper y Mimic3.

---

## Cambios hechos hoy

1. **Corrección de `voice_chat_loop.py`**
   - Se comentó la llamada a `pipeline.build_graph()` porque el grafo de Pipecat todavía es un stub y no es necesario para este modo.
   - Se agregó el import correcto:
     - `from lucy_voice.pipeline_lucy_voice import LucyVoicePipeline, LucyPipelineConfig`
   - Resultado:
     - `python -m lucy_voice.voice_chat_loop` ahora inicia sin errores.

2. **Prueba manual del modo voz por turnos**
   - Comandos usados:
     ```bash
     cd ~/Lucy_Workspace/Proyecto-VSCode
     source .venv-lucy-voz/bin/activate
     python -m lucy_voice.voice_chat_loop
     ```
   - Comportamiento observado:
     - Aparece:
       - `Lucy voz (modo VOZ).`
       - `Cada turno:`
       - `  - Apretá Enter solo para grabar`
       - `  - Escribí 'salir' y Enter para terminar`
       - `[Enter=hablar | 'salir'=terminar]:`
     - Al apretar **Enter**:
       - Lucy graba unos segundos.
       - El usuario dice “¿me escuchás?”
       - Lucy responde en voz: “sí, ¿en qué te puedo ayudar?” (u otra frase similar, clara).
       - Vuelve a mostrarse `[Enter=hablar | 'salir'=terminar]:`
     - Al escribir `salir` y Enter:
       - Muestra: `[LucyVoiceVoiceChat] Fin de la sesión de voz. Chau 💜`
       - Vuelve al prompt de Linux.

---

## Estado funcional actual (resumen para futuro)

- **Modo texto**:
  - `python -m lucy_voice.pipeline_lucy_voice`
  - Sirve para charlar con Lucy por consola, sin audio.

- **Modo voz – una sola ronda**:
  - `./scripts/lucy_voice_mic_roundtrip.sh`
  - Escucha → entiende → responde por voz → vuelve a la consola.

- **Modo voz – conversación por turnos (push-to-talk)**:
  - `python -m lucy_voice.voice_chat_loop`
  - Varios turnos:
    - Enter = hablar
    - Lucy responde en voz
    - `salir` = terminar sesión

Todo esto está usando:
- LLM local vía Ollama (`gpt-oss:20b`)
- ASR local con `faster-whisper` (modelo `small`, CPU, español)
- TTS local con Mimic3 (voz en castellano)

---

## Próximos pasos previstos (según hoja de ruta)

1. **Hotword / wake word (“hola Lucy”)**
   - Implementar un modo en el que Lucy esté “apagada pero escuchando bajito”.
   - Cuando detecta la frase “hola Lucy”, dispare _un turno_ completo equivalente a `voice_chat_loop` (escuchar → entender → responder en voz).

2. **Integración más profunda con Pipecat**
   - Migrar el flujo actual de:
     - micrófono → ASR → LLM → TTS
   - a un grafo real de Pipecat con nodos de audio y estados claros (escuchando / pensando / hablando).

3. **Tool calling + LucyTools**
   - Permitir que Lucy, además de hablar, pueda ejecutar acciones de escritorio (abrir aplicaciones, capturas, etc.) de forma segura, usando JSON de herramientas y el módulo `lucy_tools.py`.

