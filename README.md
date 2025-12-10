# Lucy Voice - Asistente de Voz Local (Nodo Modular)

> Última actualización automática: 2025-12-01 23:20:58 -03

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
- **LLM:** Ollama (p. ej. `gpt-oss:20b`)
- **TTS:** Mimic3 (`es_ES/m-ailabs_low` u otra voz)
- **VAD:** `webrtcvad` para modo manos libres
- **Comando de sueño:** "lucy dormi" / "lucy dormí" para terminar la sesión por voz

El pipeline Pipecat + wakeword ONNX vive ahora en `legacy/` y solo se conserva como referencia histórica.

📦 Para detalles sobre módulos legacy, backups y código experimental que no forma parte de Lucy Voz v2, ver `docs/LUCY-MODULOS-LEGACY.md`.

---

## 2. Características principales (modo modular)

- ✅ **Modo manos libres** con VAD  
  Presionás **Enter una sola vez** y Lucy entra en un bucle:
  escucha → transcribe → piensa → habla → vuelve a escuchar.

- ✅ **Comando de sueño por voz**  
  Si la transcripción contiene el comando de cierre (por ej. _"lucy dormi"_), Lucy:
  - confirma que recibió la orden
  - cierra la sesión de forma limpia

- ✅ **100% local / offline**  
  - Whisper local
  - Ollama local
  - Mimic3 local

- ✅ **Parámetros visibles**  
  En cada arranque se muestran (en la terminal):
  - voz Mimic3
  - `Emotion exaggeration`
  - `CFG weight`
  - modelo LLM actual (`gpt-oss:20b`, etc.)

---

## 3. Requisitos

- Linux (probado en Ubuntu)
- Python 3.12+
- Ollama instalado y corriendo (con el modelo que quieras usar, por ejemplo `gpt-oss:20b`)
- Mimic3 instalado
- Micrófono y salida de audio configurados

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
   Using Mimic3 voice: es_ES/m-ailabs_low
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
