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
## Resumen actualizado de Lucy Voz – Fase 2 (post-reinicio)

### 1. Dónde estamos hoy

Lucy Voz está corriendo de forma **100% local** en esta PC con Linux (Ubuntu), con un pipeline completo:

- **Texto → LLM → texto** (chat por consola).
- **Voz (micrófono) → texto (ASR)**.
- **Voz → texto → LLM → texto → voz (TTS)**.

Todo esto está:

- instalado,
- probado,
- versionado en la rama `main`,
- y subido a GitHub en el repo `Proyecto-VSCode`.

### 2. Qué hay instalado y funcionando

#### 2.1. Entorno V.S.Code + LLM local

- Ubuntu Desktop funcionando como sistema principal.
- **Ollama** instalado y operativo.
- Modelo local **`gpt-oss:20b`** descargado y respondiendo bien:
  - Verificado con: `ollama run gpt-oss:20b "Decime en una frase corta: Lucy está lista para trabajar."`
- **VS Code** instalado.
- Extensión **Continue** configurada para usar el modelo local vía `http://localhost:11434`.
- Repo clonado en:
  - `~/Lucy_Workspace/Proyecto-VSCode`
- Rama `main` limpia y sincronizada con GitHub.

Scripts útiles:

- `./scripts/check_deps.sh` → verifica `git`, `curl`, `wget`, `gcc`, `python3`, `node`, `docker`, `ollama`.
- `./scripts/install_deps.sh` → lista comandos de instalación sugeridos para dependencias.

#### 2.2. Entorno de voz (`lucy_voice`) – Fase 1 cerrada

- Carpeta del módulo: `~/Lucy_Workspace/Proyecto-VSCode/lucy_voice/`
- Entorno virtual:
  - `.venv-lucy-voz/` (creado con `python3 -m venv .venv-lucy-voz`)
  - Activación: `source .venv-lucy-voz/bin/activate`
- Dependencias instaladas desde `lucy_voice/requirements.txt`:
  - `faster-whisper` (ASR, modelo `small`, CPU, `int8`).
  - `mycroft-mimic3-tts` (TTS en castellano).
  - `openwakeword` (wake word básica).
  - `pipecat-ai` (orquestador de audio para el futuro).
  - `sounddevice` (captura de micrófono).
  - `pyautogui` (LucyTools / automatización).
  - Otras dependencias de audio y utilitarias.

Tests ya corridos y OK:

- `lucy_voice/check_env.py` → importa todas las libs.
- `lucy_voice/tests/test_asr_from_tts.py` → prueba de ASR sobre WAV de TTS.
- `lucy_voice/tests/test_pipecat_import.py` → Pipecat instalado.
- `lucy_voice/tests/test_openwakeword_basic.py` → motor OpenWakeWord funcional.
- `lucy_voice/tests/test_lucy_tools_screenshot.py` → genera captura de pantalla con LucyTools.
- TTS Mimic3 probado manualmente, por ejemplo:
  - `mimic3 --voice es_ES/carlfm_low "Prueba de voz de Lucy." | aplay`

#### 2.3. Pipeline de Lucy Voz – Fase 2 (estado actual)

Clase principal: `LucyVoicePipeline` en `lucy_voice/pipeline_lucy_voice.py`

Config mínima (`LucyPipelineConfig`):

- `asr_model_size = "small"`
- `asr_samplerate = 16000`
- `tts_voice = "es_ES/carlfm_low"`
- `llm_model = "gpt-oss:20b"`

Capacidades confirmadas:

1. **Texto → LLM → texto**

   - Método: `run_text_roundtrip(user_text)`
   - Usa `ollama run gpt-oss:20b`.
   - System prompt fija a Lucy como asistente de voz local, en castellano rioplatense.
   - Probado con:
     ```bash
     ./scripts/lucy_voice_chat.sh
     ```
   - Ejemplo observado:
     - Usuario: `hola`
     - Lucy: `¡Hola! ¿Cómo estás?`

2. **Voz → texto (ASR desde micrófono)**

   - Graba audio con `_record_mic_to_wav(duration_sec=5.0)`.
   - Transcribe con `_asr_transcribe_wav(...)` usando `faster-whisper small` en CPU.
   - Método de alto nivel: `run_mic_to_text_once()`.
   - Muestra idioma detectado, confianza y texto reconocido.

3. **Roundtrip completo: voz → texto → LLM → texto → voz**

   - Método: `run_mic_llm_roundtrip_once(duration_sec=5.0)`
   - Flujo:
     1. Graba unos segundos desde el micrófono.
     2. Transcribe el audio (ASR).
     3. Une los segmentos en `user_text`.
     4. Llama a `run_text_roundtrip(user_text)` (LLM local).
     5. Llama a `_speak_with_tts(answer)`:
        - `mimic3 --voice es_ES/carlfm_low`
        - Reproducción con `aplay`
     6. Imprime:
        - idioma detectado y confianza,
        - texto reconocido,
        - respuesta de Lucy.

   - Script rápido para usarlo:
     ```bash
     ./scripts/lucy_voice_mic_roundtrip.sh
     ```
   - Ejemplo observado recientemente:
     - Usuario (voz): *“Hola, 1, 2, 3, hola Lucy, ¿me escuchás?”*
     - Texto reconocido: `Hola, 1, 2, 3, Hola, Lucy, ¿me escuchas?`
     - Respuesta de Lucy (texto): `¡Hola! Sí, te escucho. ¿En qué te puedo ayudar?`
     - Respuesta de Lucy (voz): reproducida correctamente por Mimic 3.

---

### 3. Próximos pasos claros

A partir de este estado sólido, los siguientes pasos de desarrollo para Lucy Voz – Fase 2 son:

1. **Limpiar el output del LLM**
   - Filtrar los prefijos tipo:
     - `Thinking...`
     - explicaciones internas en inglés
   - Quedarse solo con la respuesta final “en personaje” para:
     - mostrar en consola,
     - mandar a TTS.

2. **Manejo half-duplex (hablar vs escuchar)**
   - Definir estados internos: `listening`, `thinking`, `speaking`.
   - Mientras Mimic 3 está hablando, Lucy **no** debe escuchar ni grabar.
   - Al terminar el TTS, volver automáticamente a modo escucha.

3. **Wake word “hola Lucy” con OpenWakeWord**
   - Configurar o entrenar un modelo para la frase “hola Lucy”.
   - Implementar un loop ligero de escucha continua:
     - mientras tanto, solo wake word,
     - al detectar “hola Lucy” → disparar `run_mic_llm_roundtrip_once()`.

4. **Integración de LucyTools (acciones sobre la máquina)**
   - Conectar el LLM a funciones de `lucy_tools.py` (tool calling simple):
     - `tomar_captura()`
     - `abrir_aplicacion(...)`
     - etc.
   - Hacer que Lucy pueda:
     - ejecutar la acción,
     - narrar lo que hizo por voz,
     - y dejar trazas en consola.

5. **Migrar la orquestación a Pipecat**
   - Reemplazar el marcador de `_graph` con un grafo real:
     - nodos de entrada de audio, wake word, ASR, LLM, TTS, salida.
   - Usar Pipecat para manejar:
     - estados (escuchando/pensando/hablando),
     - extensiones futuras (VAD, diarización, múltiples canales).

6. **Capa de interfaz / UX**
   - Diseñar una pequeña capa visual o textual mejorada para mostrar:
     - “escuchando / pensando / hablando / ejecutando acción”.
   - Opciones:
     - consola enriquecida,
     - GUI simple,
     - o un panel en VS Code.

---

Este resumen deja fijado el punto actual del proyecto después del reinicio:  
Lucy corre localmente, escucha por micrófono, procesa con un modelo open-source en Ollama y responde tanto en texto como en voz, sobre una base ya documentada y versionada en Git y GitHub.
