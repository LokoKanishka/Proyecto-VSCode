# Handoff: Ticket A9 (Hardening sprint)

**Fecha:** 2026-01-13
**Rama:** `a9-hardening-8h`

## Resumen de Cambios

Se realizó un sprint de hardening enfocándose en robustez, UX y observabilidad.

1.  **Copiado Robusto (ChatGPT)**:
    *   Nuevo script `scripts/chatgpt_copy_messages_strict.sh` con validación anti-sidebar y jitter.
    *   Integrado en el flujo `ask`.
    *   **Fix crítico**: Se arregló `x11_file_agent_start.sh` que no exportaba variables de entorno, causando fallos en IPC.
    *   Verify: `./scripts/verify_chatgpt_copy_strict.sh` (requiere ventana activa/logueada).

2.  **Motor de Diálogos UI**:
    *   Nuevo watcher `scripts/ui_dialog_watch.sh` basado en reglas (`config_ui_dialogs.yaml`).
    *   Soporta acciones como Enter, Escape, Click Relativo.
    *   Activación opcional en flujos.
    *   Verify: `./scripts/verify_ui_dialogs_local_modal.sh` (smoke test local).

3.  **YouTube Direct URL**:
    *   Mejora en `lucy_web_agent/youtube_agent.py`.
    *   Preferencia por `watch?v=` directo.
    *   Fallback a SearXNG si `yt-dlp` falla o no está instalado.
    *   Tests: `python3 -m unittest tests/test_youtube_agent_selection.py`.

4.  **Configuración & Doctor**:
    *   Unificación en `lucy_tools/config_loader.py`.
    *   Script de validación: `./scripts/validate_config.sh`.
    *   **Botón Rojo**: `./scripts/verify_repo_fast.sh` (compila, testea unitarios, valida config).

5.  **CI**:
    *   Workflow en `.github/workflows/ci.yml`.

## Instrucciones de Verificación

Para verificar el estado actual del repo ("Botón Rojo"):

```bash
./scripts/verify_repo_fast.sh
```

Para verificar subsistemas específicos (requieren entorno gráfico):

```bash
# Verify Copy (necesita ChatGPT abierto)
./scripts/verify_chatgpt_copy_strict.sh

# Verify UI Dialogs (necesita Chrome)
./scripts/verify_ui_dialogs_local_modal.sh
```

## Activación del Watcher

Para activar el watcher de diálogos durante la operación normal, exportar:

```bash
export LUCY_UI_DIALOGS=1
```

## Estado Conocido

*   La verificación visual (X11) puede fallar en entornos headless si no se levanta ventana real.
*   El IPC de X11 fue reparado y debería funcionar si el agente se levanta correctamente.
