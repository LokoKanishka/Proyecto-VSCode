# ChatGPT UI Bridge (X11) — perfiles/targets + guardrails

Este módulo permite que Lucy “hable” con ChatGPT vía UI (X11) y soporta targets explícitos para elegir la ventana correcta.

## Idea clave

- Modo target explícito: `CHATGPT_TARGET={paid|free|dummy}`.
  - `paid`: usa Chrome normal abierto (modo progreso, crea chats en la cuenta paga).
  - `free`: usa Chrome dedicado con `--user-data-dir` (guardrails estrictos).
  - `dummy`: usa el harness local (`ui_dummy_chat.html`), sin tocar ChatGPT real.
- En `free`, se valida por cmdline (user-data-dir) y `WM_COMMAND` si está disponible.
- Si el target no matchea, **se aborta** antes de tipear.

Variables clave:
- `CHATGPT_TARGET` (default `paid` en fase de progreso)
- `CHATGPT_CHROME_USER_DATA_DIR` (default `~/.cache/lucy_chrome_chatgpt_free`)
- `CHATGPT_PROFILE_NAME` (default `free`)
- `CHATGPT_WID_PIN_FILE` (default `~/.cache/lucy_chatgpt_wid_pin_<target>`)
- `CHATGPT_BRIDGE_CLASS` (default `lucy-chatgpt-bridge`)

Helper recomendado:
- `source ./scripts/chatgpt_profile_free_env.sh` (setea `CHATGPT_TARGET=free`)

## Scripts

### 1) `scripts/chatgpt_chrome_open.sh`
**Único punto de apertura** de Chrome para el bridge:
- Siempre usa `--user-data-dir` del perfil free.
- Usa `--class "${CHATGPT_BRIDGE_CLASS}"`.
- Se ejecuta en el host vía `x11_host_exec.sh`.

### 2) `scripts/chatgpt_get_wid.sh`
Selector seguro del WID (según target):
- Si hay pin válido, lo reutiliza (y lo re-escribe).
- Si el pin es inválido, hace recovery **sin foco**.
- En `free`: **nunca** selecciona ventanas fuera del perfil.
- En `paid`: no abre ventanas nuevas; requiere una ventana ChatGPT ya abierta.
- En `dummy`: busca la ventana “LUCY Dummy Chat”.

### 3) `scripts/chatgpt_bridge_ensure.sh`
Asegura que exista la ventana bridge:
- En `free`: si no existe, abre con `chatgpt_chrome_open.sh`.
- En `paid/dummy`: no abre ventanas nuevas.

### 4) `scripts/chatgpt_ui_ask_x11.sh`
Hace la pregunta por UI y espera `LUCY_ANSWER_...`:
- Rechaza WIDs que **no** matcheen el perfil (`PROFILE_GUARD_TRIPPED`).
- Deja forenses en `LUCY_ASK_TMPDIR` si falla.

## Dummy harness (sin tocar ChatGPT real)

Para validar el pipeline X11 (type → enter → copy → parse) sin generar chats:

- HTML: `diagnostics/ui_dummy_chat.html`
- Verify: `scripts/verify_ui_dummy_pipe.sh`

Esto abre el dummy con el **mismo perfil** y valida que el parse funcione.

## Troubleshooting rápido

* “ERROR: PROFILE_GUARD_TRIPPED”:
  - Asegurate de haber logueado el **perfil free** en el Chrome bridge.
  - Usá `scripts/chatgpt_profile_free_env.sh` antes de correr verifies.

* “ERROR: no encuentro ventana ChatGPT en el perfil ...”:
  - Corré `./scripts/chatgpt_bridge_ensure.sh`
  - Si no aparece, abrí manualmente ChatGPT en el perfil free.

## Target paid (modo progreso)

En `CHATGPT_TARGET=paid`, el bridge no usa perfil dedicado:
- Busca un Chrome “no-free” y **navega automáticamente** a `chatgpt.com` si no hay tab abierta.
- Esto crea chats de prueba en la **cuenta paga** (aceptado en esta fase).
- Script: `scripts/chatgpt_paid_ensure_chatgpt.sh`.

### Thread fijo de pruebas (paid)

- Archivo: `~/.cache/lucy_chatgpt_paid_test_thread.url`
- Script: `scripts/chatgpt_paid_ensure_test_thread.sh`
- En paid, cada ask verifica que la URL actual **coincida** con el thread de pruebas.
- Si no coincide, intenta navegar al thread; si falla, aborta con `WRONG_THREAD` y deja forenses.
