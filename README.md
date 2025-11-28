# Lucy Voice - Asistente de Voz Local

> **Última actualización**: 2025-11-28 15:55:59 (UTC-3)

Sistema de asistente de voz completamente local y open source, con detección de wake word personalizada, conversación continua y capacidad de ejecutar herramientas del sistema.

## 🎯 Características

- ✅ **Wake Word Personalizada**: Modelo custom "Hola Lucy" entrenado con OpenWakeWord
- ✅ **Conversación Continua**: Modo conversacional natural con VAD (Voice Activity Detection) y Pipecat
- ✅ **Herramientas del Sistema**: Abrir aplicaciones, URLs, tomar capturas, escribir texto
- ✅ **100% Local**: Sin servicios cloud, total privacidad
- ✅ **Voz Neural Femenina**: TTS con Mimic3 (LJ Speech)

## 🛠️ Stack Tecnológico

- **Pipeline**: Pipecat (Async graph)
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

# Crear entorno virtual e instalar dependencias
./scripts/install_deps.sh
```

## 🎮 Uso

### Iniciar Lucy (Modo Wake Word)

Este es el modo principal. Lucy escuchará "Hola Lucy" (o "Hey Jarvis" si no hay modelo custom).

```bash
./scripts/lucy_voice_wakeword.sh
```

### Flujo de Conversación

1. **Activación**: Di "Hola Lucy"
2. **Conversación**: Habla normalmente. Lucy detectará cuando termines de hablar.
3. **Herramientas**: Pide "Abrí el navegador" o "Tomá una captura".
4. **Terminar**: Lucy se queda escuchando hasta que digas "Chau" o pase el tiempo de espera (configurable).

## 📁 Estructura del Proyecto

```
Proyecto-VSCode/
├── lucy_voice/
│   ├── pipeline/
│   │   ├── pipecat_graph.py        # Definición del grafo Pipecat
│   │   └── processors/             # Nodos del pipeline (ASR, LLM, TTS, VAD, WakeWord)
│   ├── wakeword/
│   │   ├── listener.py             # Entrypoint del listener
│   │   └── train.py                # Entrenamiento de modelo custom
│   ├── tools/
│   │   └── lucy_tools.py           # Herramientas del sistema
│   └── config.py                   # Configuración centralizada
├── scripts/
│   ├── lucy_voice_wakeword.sh      # Script de inicio
│   └── lucy_voice_ptt.sh           # Modo Push-to-Talk (Legacy)
└── docs/
    ├── ARCHITECTURE.md             # Detalles de arquitectura
    └── USAGE.md                    # Guía de uso detallada
```

## 🔧 Configuración

Editar `config.yaml` en la raíz del proyecto:

```yaml
ollama_model: "gpt-oss:20b"
wakeword_threshold: 0.15
sample_rate: 16000
```

## 🎓 Entrenar Wake Word Custom

Si querés entrenar tu propio modelo:

```bash
# 1. Grabar muestras positivas (decir "Hola Lucy" 20+ veces)
python -m lucy_voice.wakeword.record_positive

# 2. Grabar muestras negativas (hablar sin decir "Hola Lucy")
python -m lucy_voice.wakeword.record_negative

# 3. Entrenar modelo
python -m lucy_voice.wakeword.train
```

## 🐛 Troubleshooting

Ver `docs/USAGE.md` para más detalles.

## 📝 Licencia

MIT

## 👥 Autor

LokoKanishka

