Estado del proyecto Lucy Voz – Fase 2

Fecha: 2025-11-16
Repo: ~/Lucy_Workspace/Proyecto-VSCode

1. Propósito de este documento

Este archivo registra el estado real y probado de Lucy Voz dentro del proyecto V.S.Code al día 2025-11-16.
Sirve para:

Saber qué está instalado, probado y versionado.

Poder reconstruir el entorno después de un reinicio o en otra máquina.

Tener claro qué partes de la Fase 2 están cerradas y cuáles siguen pendientes.

2. Foto general del proyecto V.S.Code
2.1. Carpeta raíz

Ruta principal del entorno de trabajo: ~/Lucy_Workspace/Proyecto-VSCode

2.2. Archivos y piezas clave

README.md

Describe el objetivo del proyecto: usar VS Code como “cabina de mando” con IA local (Ollama + modelos open source) y todo versionado en Git.

Indica cómo clonar el repo y levantar el entorno en otra máquina.

.gitignore

Ignora configuraciones locales como .vscode/ y el entorno virtual .venv-lucy-voz/, entre otras.

AGENTS.md

Define reglas para cualquier agente/IA que opere dentro del repo:

No modificar nada fuera del árbol del proyecto.

No borrar scripts sin dejar alternativa.

Respetar la preferencia por herramientas open-source, offline y sin costo.

Define el “modo Lucy” dentro de V.S.Code.

scripts/check_deps.sh

Script para verificar dependencias de sistema:

git, curl, wget

gcc / toolchain de compilación

python3

node

docker

ollama

En esta máquina ya se ejecutó y todas las dependencias marcan [OK].

scripts/install_deps.sh

Lista comandos sugeridos de instalación (apt install ...).

No instala automáticamente: el usuario decide qué ejecutar.

continue.config.example.json

Configuración de ejemplo para la extensión Continue en VS Code:

Modelo: gpt-oss:20b vía Ollama.

apiBase: http://localhost:11434.

Este archivo ya se usó como base para la config real en ~/.continue/config.json.

2.3. Infraestructura instalada y probada

En esta PC:

Ubuntu (desktop) instalado y funcionando.

Ollama instalado y levantado como servicio.

Modelo local gpt-oss:20b descargado y probado.

VS Code instalado.

Extensión Continue instalada y configurada:

VS Code puede usar gpt-oss:20b de manera local.

Repo Proyecto-VSCode sincronizado con GitHub (rama main limpia).

Resultado:
El entorno V.S.Code está listo para ser replicado: clonar el repo, correr los scripts de chequeo y copiar la config de Continue alcanza para quedar en el mismo punto.

3. Módulo lucy_voice – Fase 1 (entorno cerrado)

Ruta del módulo de voz: ~/Lucy_Workspace/Proyecto-VSCode/lucy_voice/

3.1. Estructura principal

lucy_voice/__init__.py

Marca el paquete Python.

lucy_voice/requirements.txt

Librerías clave:

pipecat-ai

faster-whisper

openwakeword

mycroft-mimic3-tts

pyautogui

sounddevice

numpy

y dependencias relacionadas.

lucy_voice/check_env.py

Script que intenta importar todas las librerías necesarias.

Se usó para validar que el entorno está bien instalado.

lucy_voice/lucy_tools.py

Primer set de herramientas para Lucy como agente:

tomar_captura(...)

abrir_aplicacion(...)

simular_teclado(...) (modo debug / futuro para automatización).

lucy_voice/tests/

__init__.py

README.md (describe las pruebas).

lucy_tts_test.wav → archivo de prueba TTS (voz de Mimic 3).

lucy_tools_screenshot.png → captura generada por tomar_captura.

test_asr_from_tts.py → prueba de faster-whisper sobre el WAV de TTS.

test_pipecat_import.py → comprueba import de Pipecat.

test_openwakeword_basic.py → prueba mínima de OpenWakeWord.

test_lucy_tools_screenshot.py → prueba de la herramienta de captura.

Entorno virtual local (no versionado): .venv-lucy-voz/

Creado con python3 -m venv .venv-lucy-voz.

Activado con source .venv-lucy-voz/bin/activate.

Dependencias instaladas con pip install -r lucy_voice/requirements.txt.

3.2. Pruebas realizadas (Fase 1)

python lucy_voice/check_env.py

Todas las librerías importan correctamente.

TTS – Mimic 3

Se generó lucy_tts_test.wav.

Escuchado con un reproductor de audio, voz clara.

ASR – faster-whisper

python lucy_voice/tests/test_asr_from_tts.py

El modelo small en CPU (int8) procesa el WAV sin errores.

Pipecat

python lucy_voice/tests/test_pipecat_import.py

Confirma instalación y versión.

OpenWakeWord

python lucy_voice/tests/test_openwakeword_basic.py

El motor corre en CPU y devuelve puntuaciones de detección (test básico, sin wake word personalizada).

LucyTools

python lucy_voice/tests/test_lucy_tools_screenshot.py

Genera lucy_tools_screenshot.png y verifica su existencia.

Conclusión Fase 1:
El entorno de voz (dependencias, TTS, ASR, detección básica de wake word, herramientas de automatización y tests) está operativo y documentado.

4. Módulo lucy_voice – Fase 2: pipeline actual

En la Fase 2 se empezó a construir el pipeline de Lucy Voz.

Archivos nuevos relevantes:

lucy_voice/pipeline_lucy_voice.py

scripts/lucy_voice_chat.sh

4.1. Camino texto → LLM → texto

Función principal: run_text_roundtrip(user_text)

Usa el modelo local gpt-oss:20b vía Ollama.

Modos de uso:

interactive_loop() dentro de pipeline_lucy_voice.py → chat por consola.

Script scripts/lucy_voice_chat.sh → arranca rápido el chat textual desde la terminal.

Estado:
Probado y funcionando: se puede mantener un diálogo textual con Lucy usando el modelo local.

4.2. Camino voz → texto (ASR desde micrófono)

Función: run_mic_to_text_once()

Acciones:

Graba unos segundos desde el micrófono usando una función interna (_record_mic_to_wav).

Guarda un archivo WAV temporal.

Lo pasa por otra función (_asr_transcribe_wav) que usa faster-whisper small en CPU (int8).

Muestra el texto reconocido en la consola.

Estado:
Ejecutado y probado: el flujo de audio de micrófono a texto funciona de punta a punta.

4.3. Camino completo voz → texto → LLM → texto

Función central: run_mic_llm_roundtrip_once()

Flujo:

Graba algunos segundos desde el micrófono a WAV.

Transcribe el audio con _asr_transcribe_wav().

Junta los segmentos en un único user_text.

Llama a run_text_roundtrip(user_text).

Imprime:

Texto reconocido del usuario.

Respuesta generada por Lucy usando el modelo local gpt-oss:20b.

Estado:
Probado manualmente en consola.
El pipeline “oído + cerebro” está funcionando en un solo archivo Python.

Este avance está versionado en el commit:

Lucy voz Fase 2: roundtrip mic→ASR→LLM en pipeline
y subido a GitHub en la rama main.

5. Qué falta de la Fase 2 (pendientes)

Del plan original de la Fase 2 quedan pendientes:

Integración de TTS en el pipeline

Que la respuesta del LLM no solo se imprima en texto, sino que también:

Se convierta en audio (Mimic 3 u otro TTS open source).

Se reproduzca automáticamente al final de cada interacción.

Manejo half-duplex (hablar/escuchar)

Cuando Lucy está hablando, el sistema no debe escuchar ni grabar.

Cuando Lucy termina de hablar, vuelve al modo escucha.

Implica coordinar captura de micrófono, reproducción de TTS y estados internos.

Wake word (“hola Lucy”) integrada al loop

OpenWakeWord ya está instalado y probado en forma básica.

Falta:

Definir o entrenar un modelo para la frase “hola Lucy”.

Integrar el detector al pipeline real:

Escucha continua de bajo costo.

Activar grabación + LLM solo cuando se detecta la wake word.

Conexión con LucyTools (acciones en la máquina)

lucy_tools.py existe y está probado por separado.

Falta:

Integrar un mecanismo de “tool calling” desde el LLM:

Interpretar la intención del usuario.

Llamar funciones como tomar_captura, abrir_aplicacion, etc.

Devolver un reporte de lo que se hizo.

Integración con Pipecat

Pipecat ya está instalado y su importación está probada.

Falta usarlo para:

Encadenar nodos de audio (entrada mic, ASR, LLM, TTS, salida).

Manejar mejor los estados (escuchando, pensando, hablando).

Preparar el futuro half-duplex y la wake word en una arquitectura más modular.

Capa de interfaz (GUI ligera o indicadores)

Pendiente diseñar algún mecanismo visual:

Estado de Lucy: “escuchando / pensando / hablando / ejecutando herramienta”.

Puede ser una GUI mínima o indicadores mejorados en consola.

6. Resumen final al 2025-11-16

El proyecto V.S.Code ya funciona como entorno base reproducible:

Repo en GitHub, scripts de chequeo, Continue configurado con gpt-oss:20b en Ollama.

El módulo lucy_voice tiene la Fase 1 cerrada:

Entorno de voz completo, librerías instaladas, tests para TTS, ASR, wake word básica, Pipecat y LucyTools.

Dentro de la Fase 2, el avance clave es:

Un pipeline real de:

texto → LLM → texto

voz → texto

voz → texto → LLM → texto

Todo probado en consola y versionado en el repo.

La siguiente etapa natural de la Fase 2 será:

Agregar TTS al pipeline, half-duplex, wake word “hola Lucy” funcional y tool calling con LucyTools, idealmente sobre una arquitectura orquestada con Pipecat.

Este documento deja registrada la foto completa de Lucy Voz en la fecha indicada y sirve como base para planificar las próximas iteraciones.
