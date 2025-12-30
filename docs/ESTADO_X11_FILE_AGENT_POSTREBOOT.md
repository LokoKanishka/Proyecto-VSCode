# Estado X11 file-agent (post-reboot) — fix "pipe_read"

## Síntoma
- `scripts/x11_file_agent.py` queda en `pipe_read` y no consume `diagnostics/x11_file_ipc/inbox/`
- `scripts/x11_file_call.sh` se cuelga esperando `outbox/res_*.txt`
- `wmctrl -lx` parece “colgado” pero el problema real es el agent bloqueado (stdin/tty)

## Fix estable (stdin infinito + setsid)
Ejecutar en HOST (misma sesión X11):

```bash
cd ~/Lucy_Workspace/Proyecto-VSCode || exit 1
set -euo pipefail

export X11_FILE_IPC_DIR="$PWD/diagnostics/x11_file_ipc"

# Stop agent
pkill -f 'scripts/x11_file_agent\.py' || true
sleep 0.3

# stdin infinito via FIFO (evita bloqueos por stdin/EOF)
FIFO=/tmp/lucy_agent_stdin.fifo
rm -f "$FIFO"
mkfifo "$FIFO"
(nohup bash -lc "while :; do echo .; sleep 60; done >'$FIFO'" >/dev/null 2>&1 &)

# Start agent desacoplado (no depende del TTY)
setsid -f python3 ./scripts/x11_file_agent.py <"$FIFO" >>"$X11_FILE_IPC_DIR/agent.log" 2>&1

# Quick check
./scripts/x11_file_call.sh 'echo PING_OK'

```

## Verificación
- `./scripts/chatgpt_ui_smoketest.sh` debe devolver dos respuestas `LUCY_ANSWER_*: OK`.
