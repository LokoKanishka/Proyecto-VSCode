# Estado global – Proyecto V.S.Code + Lucy (15/11/2025)

Este documento resume, en un solo lugar:

- El proyecto **V.S.Code** (VS Code como “cabina de mando” con IA local).
- La **máquina física** sobre la que corre todo.
- El estado del proyecto de **Lucy voz** y su plan por fases.
- Los modelos actuales en **Ollama** pensados para agentes y para código.

---

## 1. Bloque A – Proyecto V.S.Code (VS Code como cabina de mando)

### 1.1. Objetivo

- Usar **VS Code** como centro de operaciones:
  - Donde vive el **código**, la **documentación** y los **scripts**.
  - Donde vive la **IA local** integrada (no en la nube).
- El proyecto está versionado en el repo:

  `~/Lucy_Workspace/Proyecto-VSCode`

  con remoto:

  `origin -> https://github.com/LokoKanishka/Proyecto-VSCode.git`

- Si se clona este repo y se siguen las instrucciones, se puede reproducir el entorno en otra máquina.

### 1.2. Herramientas principales

- **IA local / LLM**
  - Ollama 0.12.9 como servidor de modelos.
  - Modelos actuales:
    - `gpt-oss:20b` → modelo “pesado” de referencia para razonamiento general.
    - `anarko/qwen3-coder-flash:30b` (UD-Q4_K_XL ~32 GB VRAM) → modelo orientado a **código / agente de VS Code**, recién descargado y pendiente de pruebas finas.
- **Editor / entorno**
  - VS Code (code).
  - Extensión **Continue** instalada y configurada para usar Ollama.
  - El comportamiento de la IA dentro del repo está descrito en `AGENTS.md`
    (reglas de qué puede tocar, qué no, y preferencia por herramientas open-source, locales y sin costo).

### 1.3. Estructura básica del repo

En este momento el repo incluye, entre otros:

- `README.md` – descripción del proyecto V.S.Code, dependencias y pasos para recrear el entorno.
- `AGENTS.md` – reglas para el trabajo de agentes dentro de este repo.
- `.gitignore` – excluye `.vscode/`, entornos virtuales y archivos pesados.
- `scripts/`:
  - `check_deps.sh` – verifica que estén instalados: git, curl, wget, gcc, python3, node, docker, ollama, etc.
  - `install_deps.sh` – muestra comandos sugeridos de instalación (no ejecuta nada solo).
- `lucy_voice/` – paquete de Python para la parte de voz de Lucy (entorno, pruebas, herramientas).
- `docs/` – carpeta de documentación, donde se guarda este archivo y otros snapshots.

El árbol de trabajo está limpio y sincronizado con `origin/main`.

---

## 2. Bloque B – Máquina física y sistema

### 2.1. Hardware

- CPU: **AMD Ryzen 9 7950X** (16 núcleos / 32 hilos).
- RAM: **128 GiB**.
- GPU 1: **NVIDIA GeForce RTX 5090** (~32 GiB de VRAM), principal para modelos de IA.
- GPU 2: GPU integrada AMD Raphael.
- Discos:
  - Sistema: `/dev/sda2` (ext4) montado en `/` – ~457 GiB totales.
  - Secundario (Windows / datos): `/dev/nvme0n1` (~1,9 TiB, ntfs).

### 2.2. Sistema operativo y servicios

- Distro: **Ubuntu 24.04.3 LTS (Noble Numbat)**.
- Kernel: 6.14.0-35-generic (x86_64).
- Servicios relevantes:
  - `systemd` como init.
  - `docker` y `docker compose` funcionando.
  - `ollama.service` activo (**active (running)**), levantado como servicio de sistema.
- Red:
  - Interfaz principal: `eno1` (ethernet) en la red 192.168.0.0/24.
  - Interfaces de Docker: `docker0`, bridges `br-*`, etc.

### 2.3. Herramientas de desarrollo instaladas

Verificadas con `scripts/check_deps.sh` y/o scripts previos:

- `git`
- `curl`, `wget`
- `gcc` + `build-essential`
- `python3` + `pip3`
- `node` + `npm`
- `docker` + `docker compose`
- `ollama`
- VS Code (`code`)

Esto define el “piso mínimo” que el proyecto asume para poder funcionar.

### 2.4. Modelos en Ollama

Actualmente:

- `gpt-oss:20b`  
  - Modelo grande para razonamiento y asistencia general.
  - Usado como modelo base en Continue para tareas complejas dentro de VS Code.

- `anarko/qwen3-coder-flash:30b`  
  - Modelo cuantizado (UD-Q4_K_XL, ~32 GiB VRAM).
  - Enfocado a tareas de **programación / agente de código**.
  - Se descargó correctamente (logs de “pulling manifest… writing manifest… success”).
  - Pensado para probar si mejora la experiencia del “asistente de VS Code” frente a modelos anteriores.

Pendiente: terminar de atar este modelo nuevo al agente (Continue u otro) y verificar su comportamiento real dentro de VS Code.

---

## 3. Bloque C – Proyecto Lucy voz (estado y plan)

Lucy voz se está construyendo dentro del mismo repo `Proyecto-VSCode`, en la carpeta `lucy_voice/`, con un enfoque por fases.

### 3.1. Fase 1 – Entorno de voz (COMPLETA)

Objetivo: que cada pieza funcione sola dentro de un entorno virtual, sin todavía encastrarlas.

Elementos logrados:

1. **Entorno virtual de Python**

   - `.venv-lucy-voz/` creado en el repo (ignorando en `.gitignore`).
   - Dependencias instaladas con `pip install -r lucy_voice/requirements.txt`.
   - `lucy_voice/check_env.py` verifica que todos los módulos estén presentes.

2. **TTS – Mimic 3**

   - Instalación de Mimic 3 dentro del entorno.
   - Generación del audio de prueba `lucy_voice/tests/lucy_tts_test.wav`
     (“Hola, soy Lucy…”).
   - Se reproduce correctamente con VLC y se documenta en `lucy_voice/tests/README.md`.

3. **ASR – faster-whisper**

   - Script `lucy_voice/tests/test_asr_from_tts.py`:
     - Carga el modelo `small` en CPU (`device="cpu"`, `compute_type="int8"`).
     - Transcribe el WAV de prueba.
   - El objetivo de la Fase 1 es comprobar que el modelo se carga y procesa audio sin romperse, no aún la precisión fina.

4. **Pipecat (orquestador)**

   - `lucy_voice/tests/test_pipecat_import.py`:
     - Importa Pipecat y muestra la versión.
     - Confirma que la librería está instalada y lista para usarse como orquestador en la Fase 2.

5. **OpenWakeWord (wake word)**

   - `lucy_voice/tests/test_openwakeword_basic.py`:
     - Carga modelos por defecto (alexa, hey_jarvis, etc.).
     - Procesa un frame de “silencio” y escupe puntuaciones cercanas a 0.
   - Se comprueba que OWW funciona en CPU con ONNXRuntime.
   - Todavía **no** existe el modelo personalizado “hola Lucy”; eso queda para más adelante.

6. **LucyTools – primeras herramientas de agente**

   - `lucy_voice/lucy_tools.py` incluye:
     - `tomar_captura(...)` → usa `pyautogui.screenshot()` y guarda una PNG.
     - `abrir_aplicacion(comando)` → `subprocess.Popen` de apps como `vlc`, `firefox`, etc.
     - `simular_teclado(secuencia)` → por ahora solo imprime en modo DEBUG (sin mandar teclas reales).
   - `lucy_voice/tests/test_lucy_tools_screenshot.py`:
     - Genera `lucy_tools_screenshot.png` y verifica que exista.
   - `gnome-screenshot` instalado para que `pyautogui` pueda capturar pantalla en Linux.

Conclusión Fase 1:  
El entorno de voz está montado, todas las piezas clave (TTS, ASR, wake word, Pipecat, LucyTools) funcionan de forma **individual** dentro del venv y están documentadas.

### 3.2. Fase 2 – Encastre del pipeline (PENDIENTE)

Objetivo de la Fase 2 (planificado):

- Conectar en un solo flujo:

  `“hola Lucy”` → wake word → audio → ASR → LLM en Ollama → (opcional LucyTools) → TTS → respuesta de voz.

Bloques previstos:

1. Pipeline de audio en Pipecat:
   - Nodo de micrófono, VAD (detección de fin de frase), ASR.

2. Integración con LLM en Ollama:
   - Usar un modelo **rápido** (Llama 3.1 8B, Mistral 7B, etc.) para voz en tiempo real.
   - Mantener `gpt-oss:20b` como modelo pesado para tareas más profundas.

3. Integración con TTS:
   - Cadena completa: voz de usuario → texto → LLM → texto → Mimic 3 (y luego XTTS-v2 cuando esté estable).

4. Half-duplex:
   - Cuando Lucy habla, se pausará wake word + ASR.
   - Al terminar de hablar, se reactivan.

5. Tool-calling + LucyTools:
   - Definir esquema JSON de herramientas para que el LLM pueda pedir:
     - abrir aplicaciones,
     - tomar capturas,
     - etc.

6. GUI mínima:
   - Interfaz simple (Gradio u otra) para ver:
     - historial de mensajes,
     - estado (listening / thinking / speaking / ejecutando herramienta).

### 3.3. Fase 3 – Robustez y uso diario (A FUTURO)

Objetivo:

- Afinar latencia, estabilidad y comodidad para que Lucy voz sea utilizable todos los días.

Líneas principales:

- Optimizar tiempos (ASR, LLM, TTS).
- Entrenar un wake word “hola Lucy” robusto (menos falsos positivos/negativos).
- Mejorar la voz (migrar a XTTS-v2 como voz principal).
- Endurecer LucyTools (manejo de errores, seguridad, límites claros).
- Documentar scripts de `start Lucy` y `stop Lucy` y guías completas en `docs/`.

---

## 4. Pendientes inmediatos (al día 15/11/2025)

1. **Agente de VS Code / modelo para código**
   - Verificar el comportamiento del nuevo modelo `anarko/qwen3-coder-flash:30b` dentro del agente de VS Code.
   - Comprobar:
     - que Continue (u otra extensión) realmente está usando este modelo,
     - latencia, calidad de las respuestas y estabilidad.
   - Una vez estabilizado el agente, cerrar la “fase VS Code + IA local” del plan.

2. **Inicio de Fase 2 de Lucy voz**
   - A partir de la base de Fase 1, comenzar con:
     - pipeline de audio en Pipecat,
     - integración con un LLM rápido en Ollama,
     - respuesta de voz loop completo.

Este documento sirve como **estado global**: si mañana se retoma el trabajo, basta con leerlo para saber qué hay hecho, sobre qué máquina corre todo y cuál es el siguiente paso en la hoja de ruta.
