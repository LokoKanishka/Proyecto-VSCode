# X11 File-IPC Bridge (sandbox -> host) + Clipboard estable

## Problema
En entornos sandbox (Snap/Flatpak/Code) no hay acceso directo al socket X11 (`/tmp/.X11-unix/X0`) y los sockets (AF_UNIX/AF_INET) pueden estar bloqueados. Resultado: `wmctrl/xdotool/xclip/xsel` fallan o devuelven vacio, y la automatizacion UI no puede copiar/pegar ni focalizar ventanas.

## Solucion (arquitectura)
Se implementa un “puente host” por IPC de archivos:

- `diagnostics/x11_file_ipc/inbox/`  requests
- `diagnostics/x11_file_ipc/outbox/` responses
- `diagnostics/x11_file_ipc/payloads/` payloads temporales (stdin)

Componentes:
- `scripts/x11_file_agent.py` (HOST): corre en GNOME/host, lee inbox, ejecuta comando y escribe respuesta en outbox.
- `scripts/x11_file_call.sh` (SANDBOX): escribe request y espera response.
- `scripts/x11_host_exec.sh`: ejecucion en host (usa file-agent).
- Wrappers en `scripts/x11_wrap/` para que herramientas X11 “parezcan locales” desde sandbox:
  - `wmctrl`, `xprop`, `xdotool`
  - `xsel` (clave: fuerza `/usr/bin/xsel` en host para evitar recursion/PATH y problemas de DISPLAY)
  - `xclip` (shim sobre `xsel`)

El `PATH` se ajusta desde:
- `scripts/x11_env.sh` (pone `scripts/x11_wrap` primero)

## Bridge ChatGPT (ventana dedicada)
Identificacion robusta por perfil:
- Perfil: `~/.cache/lucy_chatgpt_bridge_profile`
- `scripts/chatgpt_get_wid.sh` detecta la ventana bridge por WM_CLASS/PID/cmdline y perfil.
- `scripts/chatgpt_bridge_ensure.sh` lanza (si no existe) Chrome con `--user-data-dir=<perfil>` y abre `https://chatgpt.com`.

## Copia/ask UI
- `scripts/chatgpt_copy_chat_text.sh` hace focus + ctrl+a/ctrl+c y lee clipboard desde wrappers (xsel -> host).
- `scripts/chatgpt_ui_ask_x11.sh` envia prompt con token y espera respuesta buscando `LUCY_ANSWER_<token>:` en el texto copiado.

## Arranque recomendado

### HOST (GNOME Terminal)
```bash
cd ~/Lucy_Workspace/Proyecto-VSCode || exit 1
export X11_FILE_IPC_DIR="$PWD/diagnostics/x11_file_ipc"
mkdir -p "$X11_FILE_IPC_DIR/inbox" "$X11_FILE_IPC_DIR/outbox" "$X11_FILE_IPC_DIR/payloads"
nohup python3 -u ./scripts/x11_file_agent.py >"$X11_FILE_IPC_DIR/agent.log" 2>&1 &
pgrep -af x11_file_agent.py
tail -n 20 "$X11_FILE_IPC_DIR/agent.log"
````

### SANDBOX (donde corre el nodo)

```bash
cd ~/Lucy_Workspace/Proyecto-VSCode || exit 1
export X11_FILE_IPC_DIR="$PWD/diagnostics/x11_file_ipc"
source ./scripts/x11_env.sh

./scripts/x11_file_call.sh 'echo PING_OK'
wmctrl -lx | head
```

## Smoke tests

Clipboard sentinel:

```bash
export X11_FILE_IPC_DIR="$PWD/diagnostics/x11_file_ipc"
source ./scripts/x11_env.sh
SENT="SENTINEL_$(date +%s)"
./scripts/x11_host_exec.sh "bash -lc 'printf %q \"$SENT\" | /usr/bin/xsel --clipboard --input; echo OK'"
timeout 5s xsel --clipboard --output | head -c 120; echo
```

Ask:

```bash
export CHATGPT_BRIDGE_PROFILE_DIR="$HOME/.cache/lucy_chatgpt_bridge_profile"
./scripts/chatgpt_ui_ask_x11.sh "Responde exactamente con: OK"
```

