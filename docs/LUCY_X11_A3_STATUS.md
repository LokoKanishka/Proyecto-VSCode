# Estado X11 / ChatGPT UI Bridge (A3)

## Cerrados (con evidencia)
- **A3.7** — `x11_dispatcher.py` procesa **argv** (no bloquea stdin).  
  Verificado: `screenshot root` devuelve `PATH ... WIDTH ... HEIGHT ...` en ~0.18s.
- **A3.8** — `screenshot <WID>` funciona (WID válido).  
  Fix clave: `_host_list_windows()` no debe pasar `None` a `_parse_wmctrl_output()`.
- **A3.9** — Selector estable de WID: **Chrome ignora `--class`**, por lo que se usa **título**.  
  `chatgpt_get_wid.sh` prioriza “ChatGPT - Google Chrome” y excluye “V.S.Code”.
- **A3.10** — `focus_window` + `type_text` (sin Enter) OK.
- **A3.11** — `send_keys Return` OK.
- **A3.12** — `chatgpt_ui_ask_x11.sh` end-to-end OK (devuelve línea `LUCY_ANSWER_<token>:`).  
  Evidencia: `LUCY_ANSWER_1767739392_32050: OK`.

## Observación pendiente (no bloqueante)
- `chatgpt_copy_chat_text.sh` en “re-test rápido” a veces copia header/sidebar (texto corto tipo “Historial del chat…”).
  Aun así, **A3.12 cerró**: dentro del flujo real de `ask`, el copy fue suficiente para detectar `LUCY_ANSWER_...`.
  Esto queda como mejora de robustez del copy (click anchors/scroll/selección en panel correcto).

## Próximos objetivos (A3.13+)
- Robustecer `chatgpt_copy_chat_text.sh` para obtener transcript confiable en frío.
- Consolidar smoke tests (A3.7..A3.12) en `scripts/verify_a3_*.sh`.
- Integración final: pipeline “ask” estable + (si aplica) posteo/adjuntos y lectura de respuesta.

<!-- SMOKE_SUITE_NOTE -->
## Smoke tests (rápidos)

Para validar todo el loop X11/IPC (A3.7–A3.12) en un solo comando:

```bash
./scripts/verify_a3_all.sh
```

Scripts individuales:

* `./scripts/verify_a3_7.sh` (screenshot root)
* `./scripts/verify_a3_8.sh` (screenshot por WID)
* `./scripts/verify_a3_10.sh` (focus + type)
* `./scripts/verify_a3_11.sh` (send_keys Return)
* `./scripts/verify_a3_12.sh` (ask end-to-end, espera `LUCY_ANSWER_...`)

