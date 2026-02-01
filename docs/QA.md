# QA Checklist y reportes

## Lista de pruebas manuales

1. `./scripts/start_web_ui.sh` arranca sin errores y muestra HTTP 200.
2. `./scripts/check_voice_pipeline.sh` confirma ASR/TTS y dependencias.
3. `./scripts/web_health_smoke.sh` responde OK en `/api/health`.
4. `./scripts/run_all_smokes.sh` genera `/tmp/lucy_smoke_summary.log` y `reports/smoke_summary.md`.
5. `./scripts/skyscanner_smoke.sh` abre Firefox (o `skyscanner_smoke_headless.sh` con `xvfb-run`) y confirma `wmctrl`.
6. `python3 -m unittest tests/test_thought_engine.py` y `python3 -m unittest tests/test_lucy_tools.py`.
7. Añadir un paso que ejecute `python3 scripts/resource_dashboard.py` para confirmar que se puede leer el log de recursos (creado por `ResourceWatcher` / `WindowWatcher`).
8. Ejecutar `./scripts/resource_smoke.sh` con la UI web funcionando para verificar `/api/resource_events`.
9. Verificar `/api/plan_log` y el panel del plan en la UI para confirmar que cada flujo Browser→Vision→Hands queda registrado (p.ej. haciendo una búsqueda de YouTube).
10. Ejecutar `./scripts/gpu_pressure_smoke.sh` con la UI levantada para simular presión de GPU y confirmar que `/api/resource_events` reporta el evento y el Manager prioriza acciones ligeras.
- `systemd/lucy_swarm.service`: habilitar con `sudo systemctl enable lucy_swarm` para que el runner arranque al inicio. La unidad ejecuta `scripts/run_swarm.sh`, reinicia al fallar y escribe logs en journald.
- Confirmar la unidad con `systemctl status lucy_swarm` y `journalctl -u lucy_swarm -f`.

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
- En Ubuntu, si `python` no existe, usar `python3` o instalar alias: `sudo apt install python-is-python3`.
- Agregar pruebas de integración que validen los nuevos watchers (GPU/ventanas), el resumen automático de `MemoryManager` y la orquestación Browser→Vision→Hands para un pedido complejo de YouTube.
