# Lucy Voice - Asistente de Voz Local (Nodo Modular)

> Última actualización automática: 2026-01-13 16:58:57 -03

Lucy es un asistente de voz **100% local y open source** pensado para correr en una PC de escritorio con Linux (Ubuntu), usando:

- Reconocimiento de voz (ASR) local
- LLM local vía **Ollama**
- TTS local con **Mimic3**
- Control de aplicaciones y herramientas del sistema

Desde fines de 2025 el **modo oficial** de Lucy Voz es el **nodo de voz modular**, y el pipeline anterior con wake word / Pipecat pasó a ser **LEGACY**.

---

## 1. Arquitectura actual (Lucy Voz v2)

La arquitectura actual se organiza así:

- **Repositorio principal:** `Proyecto-VSCode`
- **Nodo de voz modular:** submódulo en  
  `external/nodo-de-voz-modular-de-lucy`
- **Lanzador oficial de voz:**  
  `scripts/lucy_voice_modular_node.sh`
- **Acceso directo gráfico:**  
  `lucy.desktop` → apunta al lanzador anterior

El nodo modular integra:

- **ASR:** Whisper (vía `openai-whisper`)
- **LLM:** Ollama (`gpt-oss:20b` o el fusionado `gpt-oss-20b-multireasoner`)
- **TTS:** Mimic3 (por defecto `es_ES/m-ailabs_low#karen_savage`, configurable)
- **VAD:** `webrtcvad` para modo manos libres con detección optimizada de silencio
- **Wake Word:** OpenWakeWord para activación por voz (configurable en `config.yaml`)
- **Half-Duplex:** El micrófono se silencia durante la respuesta de Lucy para evitar auto-activación
- **Comando de sueño:** "lucy dormi" / "lucy dormí" para terminar la sesión por voz

El pipeline Pipecat + wakeword ONNX vive ahora en `legacy/` y solo se conserva como referencia histórica.

📦 Para detalles sobre módulos legacy, backups y código experimental que no forma parte de Lucy Voz v2, ver `docs/LUCY-MODULOS-LEGACY.md`.

## Monitoreo de recursos

Lucy registra la presión de GPU/ventanas en `logs/resource_events.jsonl` vía los watchers (`src/watchers`). Podés inspeccionar el último estado con:
```bash
python3 scripts/resource_dashboard.py
```
Y, si querés probar la replanificación en situaciones de carga, ejecutá:
```bash
./scripts/gpu_pressure_smoke.sh
```
Esto suma un evento `gpu_pressure`, consulta `/api/resource_events`, `/api/memory_summary` y `/api/plan_log`, y confirma que el backend responde con los datos esperados.
También existe un endpoint en la UI para que el frontend consulte la última lectura y eventos recientes:
```
GET /api/resource_events
```
Devuelve `summary` (GPU + ventanas) y la lista de eventos útiles para dashboards o alertas.

---

## 2. Características principales (modo modular)

- ✅ **Modo manos libres** con VAD  
  Presionás **Enter una sola vez** y Lucy entra en un bucle:
  escucha → transcribe → piensa → habla → vuelve a escuchar.

- ✅ **Wake Word (Nuevo - 2026-01)**
  Lucy puede activarse con la palabra de activación configurada (por ejemplo, "hola Lucy" cuando se entrene un modelo personalizado). Mientras tanto, usa modelos por defecto de OpenWakeWord.  
  - Configurable en `config.yaml` → `wake_word.enabled`
  - Evita activaciones accidentales y ahorra recursos

- ✅ **Half-Duplex Mode**
  El micrófono se desactiva mientras Lucy habla, eliminando ecos y auto-interrupciones.  
  - Configurable: `voice_modular.half_duplex: true`

- ✅ **Comando de sueño por voz**  
  Si la transcripción contiene el comando de cierre (por ej. _"lucy dormi"_), Lucy:
  - confirma que recibió la orden
  - cierra la sesión de forma limpia

- ✅ **100% local / offline**  
  - Whisper local
  - Ollama local
  - Mimic3 local

- ✅ **Búsqueda web robusta**  
  - SearXNG con reintentos automáticos y manejo de errores
  - Fallback a DuckDuckGo si SearXNG no responde
  - Mensajes de error amigables en español

- ✅ **Búsqueda de videos de YouTube mejorada**  
  - Extracción directa de enlaces de video (en lugar de páginas de búsqueda)
  - Mayor precisión en resultados (~85% de éxito en primer intento)

- ✅  **Comprensión de comandos complejos**  
  - Maneja instrucciones multi-paso: "abre Firefox y busca gatos"
  - El LLM está entrenado para descomponer acciones encadenadas

- ✅ **Flexibilidad de modelos LLM**  
  - Cambio de modelo sin modificar código: edita `ollama_model` en `config.yaml`
  - Soporte documentado para modelos de 7B a 70B
  - Instrucciones para LoRA fine-tuning

- ✅ **Parámetros visibles**  
  En cada arranque se muestran (en la terminal):
  - voz Mimic3
  - `Emotion exaggeration`
  - `CFG weight`
  - modelo LLM actual (`gpt-oss:20b`, etc.)

---

## 3. Requisitos

- Linux (probado en Ubuntu 24.04 LTS)
- Python 3.12+
- Ollama instalado y corriendo (con el modelo que quieras usar, por ejemplo `gpt-oss:20b`)
- Mimic3 instalado
- Micrófono y salida de audio configurados
- (Opcional) Docker para SearXNG

---

## 4. Instalación

Clonar el repo:

```bash
git clone https://github.com/LokoKanishka/Proyecto-VSCode.git
cd Proyecto-VSCode
````

Crear entorno virtual e instalar dependencias:

```bash
./scripts/install_deps.sh
```

(El script crea `.venv-lucy-voz` y resuelve las dependencias de Lucy Voz y del nodo modular.)

---

## 5. Uso rápido

### 5.1. Desde el acceso directo gráfico

1. Instalá el `.desktop` (si aún no lo hiciste):

   * Copiar `lucy.desktop` a:

     * `~/.local/share/applications/`
     * (opcional) `/usr/share/applications/` para que sea global

2. Buscá **"Lucy"** en el menú de aplicaciones y hacé clic.

3. Se abre una terminal con algo del estilo:

   ```text
   🤖 Local Voice Assistant with Mimic3 TTS
   Using Mimic3 voice: es_ES/m-ailabs_low#karen_savage
   Emotion exaggeration: 0.5
   CFG weight: 0.5
   LLM model: gpt-oss:20b

   Press Enter once to start speaking (Ctrl+C to exit).
   ```

4. Presioná **Enter una vez** para empezar el bucle de escucha.

### 5.2. Desde consola

```bash
cd ~/Lucy_Workspace/Proyecto-VSCode
./scripts/lucy_voice_modular_node.sh
```

El flujo es el mismo que con el acceso directo.

### 5.3. Auditoría de trazabilidad (silenciamientos de salida)

```bash
./scripts/audit_trazabilidad.sh
```

Genera `docs/AUDIT_TRAZABILIDAD.md` y `reports/audit_trazabilidad.json`.

### 5.4. UI Web (chat + voz)

Requisitos extra: `ffmpeg` y `soundfile` instalados en el entorno que levanta Flask.

```bash
sudo apt-get install ffmpeg libsndfile1
source .venv-lucy-voz/bin/activate
pip install -r requirements.txt
python lucy_web/app.py
# o: ./scripts/start_web_ui.sh
# Para permitir Werkzeug en dev: export LUCY_WEB_ALLOW_UNSAFE=1
```

Aclaraciones:
- `./scripts/start_web_ui.sh` detecta el primer puerto libre (empezando en `LUCY_WEB_PORT` o 5000) y anuncia la URL con host/puerto finales.
- Antes de cerrar la UI, podés usar `./scripts/stop_web_ui.sh`.
- `./scripts/web_health_smoke.sh` ejecuta un servidor momentáneo en `LUCY_WEB_PORT` (5002 por defecto) y prueba `/api/health`.
- Para instalar solo las dependencias web: `pip install -r requirements-web.txt`.

Abrí `http://localhost:5000` y verificá el indicador de backend de audio (soundfile/ffmpeg). El toggle “Wake Word Mode” activa escucha continua; las respuestas se reproducen también en el navegador si “Auto Speak Responses” está activo.

### 5.5. Pruebas y scripts útiles

 - `pip install -r requirements-web.txt` instala las dependencias mínimas para la UI.
- `./scripts/start_web_ui.sh`, `./scripts/stop_web_ui.sh` y `./scripts/web_health_smoke.sh` permiten arrancar/parar y validar el endpoint `/api/health`.
- Ejecutá `python -m unittest tests/test_thought_engine.py` para validar las utilidades del ThoughtEngine (sanitización de pasos y validación de grids/typing).
- Corre `./scripts/run_all_smokes.sh` para ejecutar health, verifier y smoke en cadena; el log queda en `/tmp/lucy_smoke_summary.log`.
- `./scripts/skyscanner_smoke.sh` abre Firefox con Skyscanner, comprueba la ventana y la cierra (requiere `wmctrl` y X11).
- `./scripts/verify_skyscanner_plan.py` valida el plan de ejemplo (requiere el entorno base con `python3` y las librerías de `src/engine`).
- `./scripts/check_voice_pipeline.sh` inicializa rápidamente LucyOrchestrator y reporta los modelos/config actuales de ASR/LLM/TTS.
- `docs/ONBOARDING.md` describe los pasos desde clonar hasta correr los smokes + heurísticas.
- `docs/DEPENDENCIES.md` resume comandos para revisar `ffmpeg`, `soundfile`, `WeRTC`, `Firefox`, `wmctrl`, etc.
- `docs/QA.md` agrupa checklist de pruebas manuales y un template de reporte.
- `./scripts/run_voice_turn.sh --wav path/to/audio.wav` sintetiza un turno completo usando un WAV y registra en `logs/voice_turns.log`.
- `./scripts/skyscanner_smoke_headless.sh` ejecuta el smoke dentro de `xvfb` si necesitás evitar usar la pantalla principal.

---

## 6. Configuración

La configuración general vive en `config.yaml` en la raíz del proyecto.

Ejemplo mínimo de parámetros relevantes:

```yaml
ollama_model: "gpt-oss:20b"
sample_rate: 16000

voice_modular:
  enabled: true
  whisper_model: "base"
  vad_sample_rate: 16000
  vad_aggressiveness: 2
  sleep_commands:
    - "lucy dormi"
    - "lucy dormí"
```

> ⚠️ El resto de claves de `config.yaml` puede variar; revisá el archivo real en tu repo local.

Para opciones de LoRA y modelo fusionado de GPT-OSS 20B, ver `docs/LUCY-LLM-GPT-OSS-LORA.md`.

Documentación ampliada del nodo modular: ver `docs/VOICE_MODULAR.md`.

---

## 7. Estructura del proyecto (resumen)

```text
Proyecto-VSCode/
├── external/
│   └── nodo-de-voz-modular-de-lucy/   # Nodo de voz modular (ASR + VAD + TTS + LLM)
├── scripts/
│   ├── lucy_voice_modular_node.sh     # Lanzador oficial (v2)
│   ├── cleanup_old_voice_system.sh    # Script de limpieza del pipeline viejo
│   └── ...                            # Otros scripts varios
├── docs/
│   ├── VOICE_MODULAR.md               # Documentación del nodo modular
│   ├── LEGACY_VOICE_PIPELINE.md       # Descripción del pipeline Pipecat legado
│   └── backup/                        # Backups automáticos de README/config
├── lucy_web/                          # Código web / tools auxiliares
├── legacy/                            # Sistema de voz viejo (wakeword + Pipecat)
├── config.yaml
├── lucy.desktop
└── ...
```

---

## 8. Pipeline viejo (LEGACY)

El sistema original de Lucy Voz estaba basado en:

* Pipeline de audio/conversación con **Pipecat**
* Wake word entrenada con **OpenWakeWord** (ej. "Hola Lucy")
* ASR con **Faster Whisper**
* Scripts de entrenamiento y prueba de wake word
* Varios scripts `fix_*` para preparar/limpiar el entorno

Todo ese código se movió a `legacy/` para que no interfiera con el flujo actual, pero se conserva como:

* referencia técnica,
* y posible base para experimentos futuros.

Para más detalle histórico, ver `docs/LEGACY_VOICE_PIPELINE.md`.

## X11 Bridge (file-IPC) - Quick map
**Objective:** automate UI (Chrome/ChatGPT) from sandbox using a host agent via file-IPC.

### Where each piece runs

**Host (GNOME Terminal / real X11 session):**
- `scripts/x11_file_agent.py` (daemon): runs X11 commands on host reading `diagnostics/x11_file_ipc/{inbox,outbox}`

**Sandbox / Lucy processes:**
- `scripts/x11_file_call.sh` -> bridges commands to the host (file-IPC)
- `scripts/x11_host_exec.sh` -> executes host commands via file-agent
- `scripts/x11_wrap/*` (`xsel`, `xclip`, `xdotool`) -> wrappers so clipboard/xdotool work from sandbox
- `scripts/chatgpt_bridge_ensure.sh` / `scripts/chatgpt_get_wid.sh` -> ensure ChatGPT bridge window and get WID
- `scripts/chatgpt_copy_chat_text.sh` -> copy chat (sanitizes control chars)
- `scripts/chatgpt_ui_send_x11.sh` / `scripts/chatgpt_ui_ask_x11.sh` -> send prompt and wait for answer

### Smoke tests

See: `docs/X11_SMOKE.md`
