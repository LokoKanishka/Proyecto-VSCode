# HANDOFF A10: Intelligent Waiter

Hemos implementado un mecanismo de "espera inteligente" (`chatgpt_wait_answer_x11.sh`) que reemplaza los timeouts fijos y reintentos ciegos antiguos.

## Componentes

1.  **`scripts/chatgpt_wait_answer_x11.sh`**
    *   **Propósito**: Monitorea el chat comprobando cambios (hash diff) y buscando una respuesta específica (`LUCY_ANSWER_<token>:`) usando un regex estricto.
    *   **Lógica**:
        *   Si hay cambios: reinicia timer de "estabilidad".
        *   Si es estable por `STABLE_SEC` (default 3s) y no hay respuesta: hace un "nudge" (Escape/End) una sola vez.
        *   Si es estable por mucho tiempo (>20s) sin respuesta: error `STUCK`.
        *   Si pasa `MAX_SEC` (default 240s): error `TIMEOUT`.
    *   **Configuración**:
        *   `CHATGPT_WAIT_MAX_SEC`: Tiempo máximo total (def 240).
        *   `CHATGPT_WAIT_STABLE_SEC`: Tiempo sin cambios para considerar "thinking paused" o "done" (def 3).

2.  **`scripts/chatgpt_ui_ask_x11.sh`**
    *   **Cambio**: Se eliminó el loop de `WATCHDOG` / `POLL`.
    *   **Nuevo flujo**:
        1.  Enviar prompt (con `LUCY_REQ_<token>`).
        2.  Llamar a `chatgpt_wait_answer_x11.sh "$TOKEN"`.
        3.  Si devuelve éxito (0), imprimir la línea de respuesta.
        4.  Si falla, generar forense y salir.

3.  **Tests**
    *   `scripts/verify_wait_answer_parser.sh`: Corre tests unitarios de la lógica de extracción de tokens (Python).

## Cómo verificar logs

Cuando se ejecuta un ask, verás en stderr:
```
__LUCY_WAIT_META__ START token=... max=240
__LUCY_WAIT_META__ t=0 changed=1 bytes=... stable=0
__LUCY_WAIT_META__ t=2 changed=0 bytes=... stable=2
...
__LUCY_WAIT_META__ FOUND bytes=...
```
Esto confirma que el waiter está monitoreando activamente el estado de generación (thinking) en lugar de dormir ciegamente.
