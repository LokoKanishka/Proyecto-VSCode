# Lucy Voice Usage Guide

## Prerequisites
- Linux (Ubuntu recommended)
- Python 3.10+
- `ffmpeg` installed (`sudo apt install ffmpeg`)
- `portaudio` installed (`sudo apt install portaudio19-dev`)

## Installation
1.  Clone the repository.
2.  Run the installation script:
    ```bash
    ./scripts/install_deps.sh
    ```
    Or manually:
    ```bash
    python3 -m venv .venv-lucy-voz
    source .venv-lucy-voz/bin/activate
    pip install -r lucy_voice/requirements.txt
    ```

## Running Lucy

### Wake Word Mode (Recommended)
This mode listens continuously for "Hola Lucy" (or "Hey Jarvis" if custom model is missing).
```bash
./scripts/lucy_voice_wakeword.sh
```

### Push-to-Talk (Legacy)
This mode requires pressing Enter to speak.
```bash
./scripts/lucy_voice_ptt.sh
```

## Configuration
Edit `config.yaml` to customize:
- **LLM Model**: `ollama_model` (default: `gpt-oss:20b`)
- **Wake Word**: `wakeword_threshold`
- **Audio**: `sample_rate` (default: 16000)

## Troubleshooting
- **Microphone issues**: Ensure your default input device is set correctly in system settings.
- **Dependencies**: If `pip install` fails on `pyaudio` or `webrtcvad`, ensure `portaudio19-dev` and `python3-dev` are installed.
