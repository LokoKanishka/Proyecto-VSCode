# INFORME_FIX_FILE_IPC_WMCTRL

## Estado inicial (sintoma)
- FILE-IPC wmctrl -d / -lx colgado y loops en inbox/outbox.
- Loop observado: agent -> x11_run.sh wmctrl -> x11_file_call.sh -> agent.

## Causa raiz
- x11_run.sh usa FILE-IPC siempre que exista el directorio por default.
- El agent ya setea X11_FORCE_LOCAL=1, pero el wrapper x11_wrap/wmctrl seguia entrando en x11_run.sh y reusando FILE-IPC, causando recursividad.

## Fix aplicado
- scripts/x11_run.sh ya tenia el bloque "LUCY_PATCH: honor X11_FORCE_LOCAL" (no se duplico).
- Se agrego sanitizacion de PATH en scripts/x11_file_agent.py para remover scripts/x11_wrap cuando ejecuta comandos, evitando re-entrada por wrappers.
- Backups generados: scripts/x11_run.sh.bak.20251230_004056 (sin cambios vs actual).

## Evidencias
- Loop (antes del fix alternativo) desde /tmp/lucy_codex_patch_run.log:
  - pstree: python3 x11_file_agent.py -> x11_run.sh wmctrl -d -> x11_run.sh wmctrl -d -> x11_file_call.sh wmctrl -d -> sleep
- Tests FILE-IPC post-fix alternativo (sin timeouts):
  - RC_M=0 con __M_DONE__ (salida incluye "Cannot open display.")
  - RC_D=0 con __D_DONE__ (salida incluye "Cannot open display.")
  - RC_LX=0 con __LX_DONE__ (salida incluye "Cannot open display.")
- Env en agent (via FILE-IPC): DISPLAY=:1, XAUTHORITY=/run/user/1000/gdm/Xauthority

## Smoketest
- /tmp/lucy_codex_smoketest.log: SMOKE_RC=1
- Error clave: bridge_ensure: ERROR no aparecio el bridge (perfil=/home/lucy-ubuntu/.cache/lucy_chatgpt_bridge_profile)

## Proximo paso recomendado
- Revisar bridge_ensure y el perfil en /home/lucy-ubuntu/.cache/lucy_chatgpt_bridge_profile.
- Confirmar acceso X11 (wmctrl local sigue diciendo "Cannot open display.") antes de reintentar el smoketest.

## Estado final (30/12/2025)

### Resolución efectiva
- El sandbox no puede conectarse al socket X11 (/tmp/.X11-unix/X1) por restricciones (EPERM).
- Solución: correr `x11_file_agent.py` en la sesión GNOME real (host) con `X11_FILE_IPC_DIR` apuntando al repo; el sandbox habla por FILE-IPC.

### Verificación final (OK)
- `wmctrl -lx` vía `scripts/x11_file_call.sh` devuelve ventanas reales (RC=0).
- `scripts/chatgpt_bridge_ensure.sh`: OK (WID estable existente).
- `scripts/chatgpt_ui_smoketest.sh`: OK (`SMOKE_RC=0`) con respuestas `LUCY_ANSWER_...: OK`.

