## Lucy Voice - Onboarding rápido

### 1. Preparar entorno

```bash
git clone https://github.com/LokoKanishka/Proyecto-VSCode.git
cd Proyecto-VSCode
python3 -m venv .venv-lucy-voz
source .venv-lucy-voz/bin/activate
pip install -r requirements.txt
pip install -r requirements-web.txt
```

### 2. Iniciar Lucy Voice

- `./scripts/start_web_ui.sh` → detecta un puerto libre, valida audio y arranca la UI web.
- `./scripts/check_voice_pipeline.sh` → valida que ASR/TTS/skills estén listos sin abrir UI.
- `./scripts/web_health_smoke.sh` → prueba `/api/health` en un puerto temporal.

### 3. Smokes y diagnósticos

- `./scripts/run_all_smokes.sh` (log en `/tmp/lucy_smoke_summary.log`, resumen en `reports/smoke_summary.md`).
- `./scripts/verify_skyscanner_plan.py` valida el plan de ejemplo.
- `./scripts/skyscanner_smoke.sh` controla Firefox para revisar flujo en la práctica.

### 4. Atajos útiles

- `./scripts/stop_web_ui.sh` cierra la UI si quedó corriendo.
- `./scripts/start_web_ui.sh && ./scripts/stop_web_ui.sh` (en secuencia) sirve para pruebas espaciadas.
- Cualquier script nuevo que necesite audio puede ejecutarse en `xvfb` si no querés ocupar la pantalla principal.

### 5. Qué mirar si algo falla

- Revisá `logs/skyscanner_smoke.log` o `/tmp/lucy_smoke_summary.log`.
- Asegurate de tener `ffmpeg`, `soundfile` y acceso a la GPU (para el LLM).
- Mirá `docs/AGENTS.md` para entender las reglas de ToT y los prompts de seguridad.
