# QA Checklist y reportes

## Lista de pruebas manuales

1. `./scripts/start_web_ui.sh` arranca sin errores y muestra HTTP 200.
2. `./scripts/check_voice_pipeline.sh` confirma ASR/TTS y dependencias.
3. `./scripts/web_health_smoke.sh` responde OK en `/api/health`.
4. `./scripts/run_all_smokes.sh` genera `/tmp/lucy_smoke_summary.log` y `reports/smoke_summary.md`.
5. `./scripts/skyscanner_smoke.sh` abre Firefox (o `skyscanner_smoke_headless.sh` con `xvfb-run`) y confirma `wmctrl`.
6. `python3 -m unittest tests/test_thought_engine.py` y `python3 -m unittest tests/test_lucy_tools.py`.
7. Validar que `status.metrics` se actualiza en la UI (panel de historia).

## Reporte de incidentes

```
Fecha: YYYY-MM-DD
Comando: (p.ej. ./scripts/run_all_smokes.sh)
Resultado: falló / exitoso
Log relevante: /tmp/lucy_smoke_summary.log (línea XX)
Estado: Abierto / Cerrado
Acciones tomadas:
- Paso 1
- Paso 2
Próximo paso recomendado: ...
```

## Resolución recomendada

- Siempre revisar `reports/smoke_summary.md` después de un smoke.
- Si falla `skyscanner_smoke.sh`, probar `SKYSCANNER_SMOKE=0` y ver `logs/skyscanner_smoke.log`.
- Para problemas de audio, correr `scripts/check_voice_pipeline.sh`.
