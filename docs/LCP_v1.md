# LUCY<->ChatGPT UI Protocol (LCP) v1

## 1) Proposito

Definir un protocolo textual minimo para:

* Enviar una instruccion a ChatGPT via UI automation.
* Recibir una respuesta parseable (1 linea).
* Encadenar pasos: pedir comando safe -> ejecutar en host -> pegar salida -> confirmar OK.
* Ser robusto ante basura UI (control chars, "Tu dijiste", banners, etc.).

Este protocolo no depende del modelo: depende de la forma del texto.

## 2) Entidades y Roles

* LUCY (orquestador): genera tokens, envia prompts, parsea respuestas, decide retries/timeouts.
* ChatGPT (UI): responde en el chat, puede agregar texto extra, pero debe poder devolver una linea exacta cuando se le exige.

## 3) Requisitos de formato

### 3.1. Tokens

Un token identifica un request unico:

* Formato: T = <unix_epoch>_<rand> (ej: 1766898131_30933)
* El token solo lo define LUCY.

### 3.2. Mensaje de Request

LUCY envia un bloque que contiene:

1. Encabezado de request:

LUCY_REQ_<T>: <instruccion humana o maquina>

2. Reglas estrictas (siempre iguales):

* "Responde SOLO con UNA linea."
* "Debe empezar EXACTAMENTE con: LUCY_ANSWER_<T>: "
* "y en esa misma linea, despues de eso, pone tu respuesta."

### 3.3. Mensaje de Answer

ChatGPT debe responder exactamente:

LUCY_ANSWER_<T>: <payload>

Donde <payload> depende del tipo.

## 4) Tipos de payload (v1)

### 4.1. ACK simple

* Payload: OK
* Uso: confirmar recepcion / sincronizacion.

Ejemplo:
LUCY_ANSWER_<T>: OK

### 4.2. Comando SAFE (whitelist)

* Payload: un comando seguro, por ahora solo:

  echo <ASCII_SAFE_TOKEN>

Regex recomendado:
^echo [A-Za-z0-9_:-]+$

Ejemplo:
LUCY_ANSWER_<T>: echo LUCY_CMD_OK_1766905220

### 4.3. Resultado pegado (LUCY -> ChatGPT)

Cuando LUCY ejecuta un comando y pega resultado:

LUCY_CMD_OUT_<E2E_ID>: <una linea>

Eso no requiere token: es evidencia.

## 5) Parsing y saneamiento

El texto copiado del chat puede venir con basura:

* \r
* control chars 0x00-0x1F
* DEL 0x7F
* prefijos invisibles antes de LUCY_REQ_...

### Regla obligatoria: sanitizar antes de parsear

Canonical sanitize:

* eliminar \r
* eliminar \x00-\x08, \x0b, \x0c, \x0e-\x1f, \x7f

Luego parsear con ancla real:

* Detectar answer con:
  ^LUCY_ANSWER_<T>: (despues de sanitizar)

Nunca aceptar coincidencias en el medio del texto porque te podes comer lineas de instruccion.

## 6) Timeouts, retries, watchdog

### 6.1. Timeout del ASK

* ASK_TIMEOUT_SEC: recomendado 22-30s (en tu evidencia: ~22s estable para loops de OK).
* Para casos lentos (voice-like ASK1): 45-60s.

### 6.2. Retry policy

* Retry si:
  * no aparece LUCY_REQ_<T> post-send (fallo foco/pegado/enter)
  * o aparece el request pero no aparece LUCY_ANSWER_<T> dentro de timeout

Retries sugeridos:

* MAX_RETRY=1 para ASK2 (OK)
* MAX_RETRY=1..2 para ASK1 (comando safe)

### 6.3. Watchdog anti-secuestro (UX safety)

* WATCHDOG_SEC: corta xdotool/copy/ask si la UI queda en loop.
* Recomendado:
  * para tests cortos: 10-16s (tu lucy_ask_safe ya lo probo)
  * para voice-like: 70s (cubre 2 asks)

Accion watchdog: ejecutar /tmp/lucy_panic.sh o equivalente versionado.

## 7) Protocolo "Voice-like E2E" (v1)

Objetivo: simular "le hablo -> pedi comando -> ejecuta -> pega output -> confirma OK".

### Pasos

1. ASK1 (comando safe)

   * Prompt: "Responde exactamente con: echo LUCY_CMD_OK_<E2E_ID>"
   * Parse: extraer payload tras LUCY_ANSWER_<T>: y validar regex safe.

2. HOST EXEC

   * Ejecutar el comando en host via x11_host_exec.sh.
   * Capturar 1 linea.

3. SEND OUTPUT

   * chatgpt_ui_send_x11.sh "LUCY_CMD_OUT_<E2E_ID>: <linea>"

4. ASK2 (OK)

   * Prompt: "Responde exactamente con: OK"
   * Reintentar 1 vez si vacio.

Exit success si:

* ASK1 valido + HOST_OUT no vacio + ASK2 == OK.

## 8) Observabilidad minima

Cada corrida debe poder dejar un log con:

* E2E_ID=...
* CHATGPT_WID_HEX=...
* ASK1_ANS=...
* CMD_OK=...
* HOST_OUT_LINE=...
* ASK2_ANS=... (+ retry si aplica)
* RC=... + DONE

## 9) Compatibilidad futura

v2 puede agregar:

* lista de comandos permitidos (cat, ls, uname, etc) con whitelists
* multiples lineas (payload base64, JSON, etc.)
* firma/hmac de payload para evitar contaminacion UI
* tool-calling local (sin depender de ChatGPT para comandos)
