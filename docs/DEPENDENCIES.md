# Dependencias críticas

Este documento lista los componentes que Lucy Voice usa y cómo verificarlos.

| Dependencia | Comando de verificación | Notas |
|-------------|-------------------------|-------|
| `ffmpeg` | `ffmpeg -version` | Necesario para decodificar audio webm/opus. Instalar con `sudo apt install ffmpeg`. |
| `libsndfile` / `soundfile` | `python3 - <<'PY'\nimport soundfile as sf\nprint(sf.__version__)\nPY` | Requiere `soundfile`. Alternativa: `pip install soundfile`. |
| `sounddevice` | `python3 - <<'PY'\nimport sounddevice as sd\nprint(sd.query_devices())\nPY` | Entrada/salida de audio en pruebas locales. |
| `WeRTC VAD` (`webrtcvad`) | `python3 - <<'PY'\nimport webrtcvad\nprint(webrtcvad.Vad.__doc__)\nPY` | Usado en `lucy_voice/pipeline/audio.py`. Si falla, reinstalar con `pip install webrtcvad`. |
| `pyautogui` | `python3 - <<'PY'\nimport pyautogui\nprint(pyautogui.size())\nPY` | Controla mouse/teclado; necesita al menos un servidor X. |
| `tesseract-ocr` | `tesseract --version` | OCR usado por `VisionPipeline` (pytesseract). Instalar con `sudo apt install tesseract-ocr`. |
| `opencv` | `python3 - <<'PY'\nimport cv2\nprint(cv2.__version__)\nPY` | Preprocesado de imágenes para visión. |
| `ultralytics` | `python3 - <<'PY'\nimport ultralytics\nprint(ultralytics.__version__)\nPY` | Detección UI con YOLOv8 (opcional). |
| `node/npm` | `node --version` | Necesario para compilar la extensión VS Code (`vscode_extension/lucy-agent`). |
| `Firefox` | `which firefox` | Navegador objetivo para la UI y smokes. |
| `wmctrl` | `wmctrl -m` | Herramienta para mover ventanas; se usa en `scripts/skyscanner_smoke.sh`. |
| `xvfb-run` (opcional) | `which xvfb-run` | Para ejecutar smokes headless (`scripts/skyscanner_smoke_headless.sh`). |

Para actualizar: `sudo apt update && sudo apt install ffmpeg libsndfile1 wmctrl firefox xvfb tesseract-ocr`.
