# Handoff: ChatGPT Bridge (X11 + Service)

## 1) Estado actual
- A3/A4/A5/A6/A7/A8 OK.
- Pin por WID a cuenta FREE (ventana dedicada en Chrome).
- Servicio por file-queue + systemd --user disponible.

## 2) Boton rojo (verifies)
- `./scripts/verify_a4_all.sh`
- `./scripts/verify_chatgpt_service_systemd.sh`
- `./scripts/verify_chatgpt_service_integration.sh`
- `./scripts/verify_no_direct_chatgpt_ui.sh`
- `./scripts/verify_chatgpt_bridge_py.sh`

## 3) Pin de la ventana correcta (FREE)
1. Click/foco en la ventana ChatGPT FREE.
2. `./scripts/chatgpt_unpin_wid.sh`
3. `./scripts/chatgpt_pin_wid.sh`

Pin file:
- `~/.cache/lucy_chatgpt_wid_pin`

Variables utiles:
- `CHATGPT_WID_PIN_ONLY=1` (falla si el pin es invalido)

## 4) Uso desde Python
CLI:
- `python3 -m lucy_agents.chatgpt_bridge "Respondé exactamente con: OK"`

API:
```python
from lucy_agents.chatgpt_bridge import ask_raw, ask

result = ask_raw("Respondé exactamente con: OK")
print(result["answer_text"])
```

## 5) Servicio (file-queue)
Manual:
- `./scripts/chatgpt_service_run.sh`

Systemd --user:
- `systemctl --user status lucy-chatgpt-service.service`
- `systemctl --user restart lucy-chatgpt-service.service`
- `systemctl --user stop lucy-chatgpt-service.service`

Cliente:
- `python3 -m lucy_agents.chatgpt_client "Respondé exactamente con: OK"`

## 6) Forense (por request)
Base:
- `/tmp/lucy_chatgpt_bridge/YYYY-MM-DD/REQ_<epoch>_<rand>/`

Archivos esperados:
- `request.txt`
- `stdout.txt`
- `stderr.txt`
- `meta.env`
- `copy.txt`
- `screenshot.png` (solo si aplica)

## 7) Problemas tipicos + solucion
- Pin apunta a ventana inexistente:
  - `./scripts/chatgpt_unpin_wid.sh` + click en la FREE + `./scripts/chatgpt_pin_wid.sh`
- "active window is not ChatGPT":
  - Foco en la ventana correcta de Chrome y reintentar pin.
- Timeout / stall:
  - Revisar `WATCHDOG_STEP` en `stderr.txt` del forense.
- Copy captura header:
  - Ver `COPY_CHOSEN` y `COPY_BYTES` en logs.
  - Revisar `copy.txt` del forense.
