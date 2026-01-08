# ChatGPT UI Bridge (X11) — perfil dedicado + guardrails

Este módulo permite que Lucy “hable” con ChatGPT vía UI (X11) **sin tocar la cuenta paga**.

## Idea clave

- El bridge usa **un Chrome dedicado** con `--user-data-dir` propio (perfil free).
- Se valida por **WM_COMMAND** + `--user-data-dir` (no solo por título/WM_CLASS).
- Si el perfil no matchea, **se aborta** antes de tipear.

Variables clave:
- `CHATGPT_CHROME_USER_DATA_DIR` (default `~/.cache/lucy_chrome_chatgpt_free`)
- `CHATGPT_PROFILE_NAME` (default `free`)
- `CHATGPT_WID_PIN_FILE` (default `~/.cache/lucy_chatgpt_wid_pin_free`)
- `CHATGPT_BRIDGE_CLASS` (default `lucy-chatgpt-bridge`)

Helper recomendado:
- `source ./scripts/chatgpt_profile_free_env.sh`

## Scripts

### 1) `scripts/chatgpt_chrome_open.sh`
**Único punto de apertura** de Chrome para el bridge:
- Siempre usa `--user-data-dir` del perfil free.
- Usa `--class "${CHATGPT_BRIDGE_CLASS}"`.
- Se ejecuta en el host vía `x11_host_exec.sh`.

### 2) `scripts/chatgpt_get_wid.sh`
Selector seguro del WID:
- Si hay pin válido, lo reutiliza (y lo re-escribe).
- Si el pin es inválido, hace recovery **sin foco**.
- **Nunca** selecciona ventanas fuera del perfil (`WM_COMMAND` + `user-data-dir`).
- Si no hay ventana, abre una nueva con `chatgpt_chrome_open.sh`.

### 3) `scripts/chatgpt_bridge_ensure.sh`
Asegura que exista la ventana bridge:
- Si ya está abierta, devuelve el WID.
- Si no, abre con `chatgpt_chrome_open.sh`.

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
