# ChatGPT UI Bridge (X11) — WID seguro + smoketest

Este módulo permite que Lucy “hable” con ChatGPT vía UI (X11) sin pegarle nunca a la ventana equivocada.

## Idea clave

- **Solo** se interactúa con la **ventana puente** (Chrome `--app`) cuya `WM_CLASS` empieza con:
  - `chatgpt.com.*`

Eso evita tocar la ventana “ChatGPT - V.S.Code - Google Chrome” u otras pestañas.

## Scripts

### 1) `scripts/chatgpt_get_wid.sh`
Selector **seguro** del WID:

- Primero respeta overrides:
  - `LUCY_CHATGPT_WID_HEX=0x...`
  - `CHATGPT_WID_HEX=0x...`
- Si no hay overrides, busca **únicamente** `WM_CLASS` `chatgpt.com.*`
- Si no existe, falla con código `2`

### 2) `scripts/chatgpt_bridge_ensure.sh`
Asegura que exista la ventana puente:

- Si ya está abierta, devuelve el WID.
- Si no está, abre:
  - `google-chrome --profile-directory=Default --app="https://chatgpt.com/"`
- Espera hasta ~15s a que aparezca `WM_CLASS chatgpt.com.*` y devuelve el WID.

### 3) `scripts/chatgpt_ui_ask_x11.sh`
Hace la pregunta por UI (pega prompt + Enter) y espera `LUCY_ANSWER_...`:

- Si no se pasó `CHATGPT_WID_HEX`, intenta:
  1) `chatgpt_bridge_ensure.sh`
  2) si no existe, `chatgpt_get_wid.sh`
- Variables:
  - `ASK_TIMEOUT` (default 75)
  - `CHATGPT_TIMEOUT_SEC` (alias del anterior)

### 4) `lucy_agents/voice_actions.py` → `_ask_chatgpt_ui()`
Integra el ask UI desde Python. Si no hay WID explícito, lo resuelve con el selector seguro.

## Smoketest E2E

Script:
- `scripts/chatgpt_ui_smoketest.sh`

Qué verifica:
- Detecta ventanas ChatGPT existentes
- Asegura/abre la ventana puente
- Ejecuta `ask_x11` **dos veces**
- Loguea a `/tmp/lucy_chatgpt_ui_smoketest_YYYYMMDD_HHMMSS.log`

Ejecutar:
```bash
./scripts/chatgpt_ui_smoketest.sh
```

Éxito esperado:

* `RC=0`
* `ASK #1` y `ASK #2` devuelven `OK`
* La ventana puente queda viva y la de “V.S.Code” también

## Troubleshooting rápido

* “ERROR: no encontré la ventana PUENTE …”

  * Corré:

    * `./scripts/chatgpt_bridge_ensure.sh`
  * Logueate en la ventana puente (perfil Default) si fuese necesario.
