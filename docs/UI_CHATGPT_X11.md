# ChatGPT UI automation (X11 / XWayland)

Estos scripts automatizan un “ask” a ChatGPT usando X11 (vía `xdotool`/`wmctrl`) y lectura de la conversación copiando texto al clipboard (vía `xclip`).

## Requisitos
Paquetes:
- xdotool
- wmctrl
- xclip

Entorno:
- Sesión X11 o Wayland con XWayland habilitado.
- `DISPLAY` accesible (por defecto `:0`).
- `XAUTHORITY` válido (el script intenta autodetectar).

## Scripts
- `scripts/chatgpt_get_wid.sh`  
  Detecta el window id (WID hex) de la ventana de Chrome que contiene el tab (prioriza tabs `LUCY_REQ_*`).

- `scripts/chatgpt_focus_paste.sh "<texto>"`  
  Enfoca la ventana y pega el texto en el input (no envía). Clickea abajo-derecha para evitar sidebar.

- `scripts/chatgpt_copy_chat_text.sh`  
  Copia el texto del chat al clipboard (clicks a la derecha para evitar sidebar) y lo emite por stdout.

- `scripts/chatgpt_extract_answer.py <LABEL>`  
  Extrae una línea `LABEL: ...` desde stdin (descarta placeholders del prompt).

- `scripts/chatgpt_ui_ask_x11.sh "<pregunta>"`  
  Pipeline completo: pega prompt, envía Enter, espera y lee hasta encontrar `LUCY_ANSWER_*`.

- `scripts/chatgpt_ui_smoke_x11.sh`  
  Smoke test “env -i”: verifica que el pipeline funcione en modo no-interactivo.

## Uso rápido

### Smoke
```bash
./scripts/chatgpt_ui_smoke_x11.sh 1>&2
```

### Ask

```bash
WID="$(./scripts/chatgpt_get_wid.sh)"
CHATGPT_WID_HEX="$WID" ./scripts/chatgpt_ui_ask_x11.sh "Respondé exactamente con: OK" 1>&2
```

## Troubleshooting

* `BadWindow (invalid Window parameter)`:
  WID viejo. Recalcular con `./scripts/chatgpt_get_wid.sh`.

* `Cannot open display` / `Failed creating new xdo instance`:
  Falta `DISPLAY`/`XAUTHORITY`. El `ask_x11` intenta setear defaults; si estás en sesión rara, exportá:
  `export DISPLAY=:0` y/o `export XAUTHORITY=...`.

* “abre/cierra chats”:
  Estaba clickeando en la sidebar. Estos scripts clickean a la derecha (70% ancho) para evitarlo.

## Dependencias

Para que funcione la UI por X11 (focus/paste/copy), necesitás:

- xdotool
- wmctrl
- xclip

Chequeo rápido:

```bash
./scripts/check_ui_deps.sh
```

## Doctor (diagnóstico rápido)

Si algo se rompe (DISPLAY/XAUTHORITY, WID, copy/paste), corré:

```bash
./scripts/chatgpt_ui_doctor.sh
````

Esto valida:

* deps (xdotool/wmctrl/xclip)
* DISPLAY/XAUTHORITY
* detección de ventana (WID)
* smoke ask (OK)
  
