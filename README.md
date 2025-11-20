# Lucy Voice - Asistente de Voz Local

Sistema de asistente de voz completamente local y open source, con detección de wake word personalizada, conversación continua y capacidad de ejecutar herramientas del sistema.

## 🎯 Características

- ✅ **Wake Word Personalizada**: Modelo custom "Hola Lucy" entrenado con OpenWakeWord
- ✅ **Conversación Continua**: Modo conversacional natural con VAD (Voice Activity Detection)
- ✅ **Interrupción por Voz**: Posibilidad de interrumpir a Lucy mientras habla
- ✅ **Herramientas del Sistema**: Abrir aplicaciones, URLs, tomar capturas, escribir texto
- ✅ **100% Local**: Sin servicios cloud, total privacidad
- ✅ **Voz Neural Femenina**: TTS con Mimic3 (LJ Speech)

## 🛠️ Stack Tecnológico

- **ASR**: Faster Whisper (Systran/faster-whisper-small)
- **LLM**: Ollama (gpt-oss:20b)
- **TTS**: Mimic3 (en_US/ljspeech_low)
- **Wake Word**: OpenWakeWord (modelo custom)
- **VAD**: webrtcvad
- **Tools**: pyautogui, subprocess

## 📋 Requisitos

- Python 3.12+
- Ollama instalado con modelo `gpt-oss:20b`
- Mimic3 instalado
- Micrófono y altavoces/auriculares

## 🚀 Instalación

```bash
# Clonar repositorio
git clone https://github.com/LokoKanishka/Proyecto-VSCode.git
cd Proyecto-VSCode

# Crear entorno virtual
python -m venv .venv-lucy-voz
source .venv-lucy-voz/bin/activate

# Instalar dependencias
pip install -r lucy_voice/requirements.txt

# Descargar voz femenina
mimic3-download en_US/ljspeech_low
```

## 🎮 Uso

### Iniciar Lucy

```bash
./scripts/lucy_voice_wakeword_loop.sh
```

### Flujo de Conversación

1. **Activación**: Di "Hola Lucy"
2. **Conversación**: Habla normalmente, Lucy responde y sigue escuchando
3. **Interrupción**: Habla fuerte mientras Lucy habla para interrumpirla
4. **Desactivación**: Di "chau Lucy", "hasta luego" o espera silencio

### Comandos de Ejemplo

- "Hola Lucy... abrí Firefox"
- "Hola Lucy... buscá 'clima Buenos Aires' en Google"
- "Hola Lucy... tomá una captura de pantalla"
- "Hola Lucy... contame sobre Pink Floyd"

## 📁 Estructura del Proyecto

```
Proyecto-VSCode/
├── lucy_voice/
│   ├── pipeline_lucy_voice.py      # Pipeline principal (ASR + LLM + TTS)
│   ├── wakeword_listener.py        # Listener de wake word
│   ├── lucy_tools.py               # Herramientas del sistema
│   ├── train_wakeword_model.py     # Entrenamiento de modelo custom
│   ├── record_wakeword_samples.py  # Grabación de muestras positivas
│   ├── record_wakeword_negatives.py # Grabación de muestras negativas
│   └── data/wakeword/
│       └── modelos/
│           └── hola_lucy.onnx      # Modelo wake word entrenado
├── scripts/
│   └── lucy_voice_wakeword_loop.sh # Script de inicio
└── docs/
    ├── LUCY-TOOLS-PROTOCOLO.md     # Protocolo de herramientas
    └── VOCES-TTS.md                # Información sobre voces TTS
```

## 🔧 Configuración

Editar `lucy_voice/pipeline_lucy_voice.py`:

```python
class LucyPipelineConfig:
    whisper_model_name: str = "Systran/faster-whisper-small"
    ollama_model: str = "gpt-oss:20b"
    tts_voice: str = "en_US/ljspeech_low"  # Cambiar voz aquí
```

## 🎓 Entrenar Wake Word Custom

Si querés entrenar tu propio modelo:

```bash
# 1. Grabar muestras positivas (decir "Hola Lucy" 20+ veces)
python -m lucy_voice.record_wakeword_samples

# 2. Grabar muestras negativas (hablar sin decir "Hola Lucy")
python -m lucy_voice.record_wakeword_negatives

# 3. Entrenar modelo
python -m lucy_voice.train_wakeword_model
```

## 🐛 Troubleshooting

### Lucy no me escucha
- Verificar que el micrófono esté funcionando
- Ajustar umbral de VAD en `pipeline_lucy_voice.py`

### Transcripciones incorrectas
- Considerar usar modelo Whisper más grande (`medium`)
- Verificar calidad del micrófono

### Interrupción muy sensible/poco sensible
- Ajustar `energy_threshold` en `_start_interruption_monitor()`

## 📝 Licencia

MIT

## 👥 Autor

LokoKanishka

## 🙏 Agradecimientos

- OpenWakeWord
- Faster Whisper
- Mimic3
- Ollama
