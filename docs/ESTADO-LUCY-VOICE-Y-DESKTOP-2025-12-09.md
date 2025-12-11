Genial, lo cerramos bien desde acá y te lo dejo listo para que el “nuevo chat” se ubique al toque. No hace falta que me aclares nada más, voy a hacer el informe completo con lo que ya tenemos.

---

## 1. Contexto general del proyecto (para el próximo chat)

Repo principal: `https://github.com/LokoKanishka/Proyecto-VSCode.git`

Arquitectura actual de Lucy (alto nivel):

* **Mente**

  * Nodo de voz modular en
    `external/nodo-de-voz-modular-de-lucy/app.py`
  * LLM local vía **Ollama** (`gpt-oss:20b`), usando LangChain.
  * Prompt de sistema en castellano rioplatense.
  * Maneja tool-calls JSON del tipo `{"name": "desktop_agent", "arguments": {...}}`.

* **Manos de escritorio (Desktop Agent)**

  * Script lanzador: `scripts/lucy_desktop_agent.sh`
  * Implementación: `scripts/lucy_desktop_agent.py`
  * Ejecuta sólo comandos de una **allowlist** (`xdg-open`, `code .`, `nautilus .`, etc.).
  * Tiene modo “un solo comando” (para Lucy) y modo interactivo.

* **Puente mente↔manos**

  * `lucy_agents/desktop_bridge.py`

    * Función clave: `run_desktop_command(command: str) -> int`
      que llama a `lucy_desktop_agent.sh` y devuelve el código de salida.

* **Intenciones de voz (“voice actions”)**

  * `lucy_agents/voice_actions.py`
  * Traduce frases tipo:

    * “abrí Google y buscá X”
    * “buscá X en YouTube”
    * “abrí VS Code”, “abrí el proyecto”
  * Genera un **plan** de acciones de escritorio y las ejecuta con `run_desktop_command`.

* **Documentación interna clave**

  * `docs/LUCY-RESUMEN-TECNICO.md` → panorama general del proyecto.
  * `docs/LUCY-DESKTOP-AGENT.md` → cómo funcionan las manos de escritorio.
  * **Nuevo**: `docs/LUCY-WEB-AGENT-PLAN.md` → plan del futuro Web Agent (para navegar como humano).

---

## 2. Qué se hizo en esta ronda de trabajo

### 2.1. Logs y robustez en la mente (`app.py`)

En `external/nodo-de-voz-modular-de-lucy/app.py` se hicieron estos cambios:

* Se agregó un helper de logging:

  ```python
  def _log(msg: str) -> None:
      print(msg, flush=True)
  ```

  y se empezó a usar para todos los mensajes `[LucyVoice] ...`.

* **Warm-up del LLM**:

  * Se añadió una función tipo `_warmup_llm(chain_with_history)` que hace una llamada corta al modelo (“Decí solo OK.”) al iniciar el nodo, para bajar la latencia de la primera respuesta.

* **Tool-calls de `desktop_agent` más robustos:**

  * Se creó `_handle_desktop_tool_json(json_str: str)` para interpretar JSON de tool-calls.
  * Ahora acepta JSON con:

    * `{"name": "desktop_agent", "arguments": {"command": "open_url", "url": "https://..."}}`
    * **y también** JSON que trae sólo `"url"` sin `"command"` → se asume `command="open_url"`.
  * Valida que la URL empiece con `http://` o `https://`.
  * Ejecuta el comando mediante Desktop Agent y loguea:

    * comando exacto,
    * código de salida.

* **Manejo de bloques `json` en la salida del LLM:**

  * Si el modelo devuelve texto con bloques de código `json` que contienen tool-calls:

    * se extraen,
    * se procesan (se ejecutan los `desktop_agent`),
    * se remueven de la respuesta hablada,
    * se deja un texto limpio para TTS.
  * Se loguea cuántas acciones de `desktop_agent` se dispararon desde JSON.

* **Fallback cuando el LLM devuelve vacío o algo raro:**

  * Si `raw` viene vacío o sólo espacios, se usa un mensaje seguro:

    > “No entendí bien qué querías que haga. Probá pedírmelo de nuevo, más despacio o en pasos separados.”

* **Logs más detallados en `get_llm_response`:**

  * Se imprime:

    * input recibido: `get_llm_response() input: ...`
    * salida cruda del modelo: `raw output: ...`
    * texto final que se va a hablar: `final spoken: ...`
  * También se loguea cuando se detectan y ejecutan tool-calls.

> Nota: el objetivo es que en los logs de consola se pueda reconstruir cada turno de la mente: qué se le pidió, qué devolvió el LLM, qué herramientas usó y qué terminó diciendo.

### 2.2. Logs en Desktop Agent (`scripts/lucy_desktop_agent.py`)

Cambios hechos:

* Helper `_log` similar al de `app.py`.
* Loguea:

  * `argv` completo al entrar.
  * El comando que realmente se va a ejecutar, por ejemplo:

    * `[LucyDesktop] Running allowed command: 'xdg-open https://www.youtube.com/results?search_query=...'`
  * El código de salida:

    * `[LucyDesktop] Command exit code: 0`
  * Si se captura `stderr`, también lo muestra (para debug de errores).

Esto deja muy claro, en consola, **qué le pidió Lucy al sistema operativo** y si funcionó.

### 2.3. Voice Actions: búsqueda vs reproducción en YouTube

En `lucy_agents/voice_actions.py`:

* Se extendió el parser de intenciones para distinguir entre:

  1. **Búsqueda simple**:

     * “buscá Alejandro Dolina en YouTube”
     * “abrí YouTube y buscá Escucho ofertas de Blender”
  2. **Pedido de reproducción / ver video**:

     * “buscá Alejandro Dolina en YouTube y reproducilo”
     * “quiero ver el programa X en YouTube”, “dale play”, etc.

* Se agregó `_wants_playback(text: str) -> bool` con un listado de frases gatillo:

  * “reproducilo”, “reproducirlo”, “ponelo”, “dale play”, “quiero verlo”, etc.

* Se agregó `_plan_targets_youtube(actions: list[PlannedAction]) -> bool`

  * Devuelve `True` si alguna acción del plan final tiene una URL con `youtube.com`.

* En `maybe_handle_desktop_intent`:

  * Se construye el plan de acciones (como antes).

  * Se calculan `wants_play` y `targets_yt`.

  * Se ejecutan igualmente los comandos del plan (abre búsqueda en YouTube, etc.).

  * **Si** `wants_play` y `targets_yt` son `True`:

    * No se pasa al LLM: la respuesta viene directamente desde `voice_actions`.
    * `spoken` se setea a algo del estilo:

      > “Te abrí la búsqueda en YouTube para ese programa, pero por ahora no puedo elegir el video ni darle play. Tenés que apretar vos en el que quieras.”

  * Se loguea cuando se detecta esta intención de reproducción.

Resultado: cuando Diego dice cosas como
“Buscá Alejandro Dolina en YouTube y reproducilo”, Lucy:

1. Abre YouTube con la búsqueda correcta (vía `xdg-open`).
2. Explica explícito que **no puede hacer clic ni dar play** todavía.

### 2.4. Plan del futuro Web Agent

Se crearon:

* `docs/LUCY-WEB-AGENT-PLAN.md`

  Contiene:

  * Objetivo del Web Agent: navegar web de forma más “humana” (abrir páginas, leer DOM, seguir links, devolver resúmenes o URLs).
  * Primer caso de uso: YouTube + “Escucho ofertas de Blender” (encontrar el programa de hoy).
  * API propuesta:

    * `find_youtube_video_url(query: str, channel_hint: Optional[str], strategy: str = "latest") -> Optional[str>`
  * Estrategia de integración:

    * El LLM usará un tool `web_agent`.
    * El Web Agent devolverá una URL final de video.
    * Desktop Agent hará el `xdg-open` de esa URL.

* Paquete Python `lucy_web_agent/`:

  * `__init__.py` expone `find_youtube_video_url`.
  * `youtube_agent.py` define la función como **stub**:

    ```python
    def find_youtube_video_url(...):
        raise NotImplementedError("Lucy Web Agent not implemented yet.")
    ```

Todavía **no hay implementación real** de Web Agent; sólo el esqueleto y el acuerdo de cómo se va a usar.

---

## 3. Estado actual de Lucy

### 3.1. Lo que Lucy sí hace hoy

* Levanta como nodo de voz modular con Mimic3 TTS (español).

* Usa STT (Whisper) para transcribir la voz de Diego.

* Antes de consultar al LLM:

  * pasa por `voice_actions` para ver si se trata de un comando de escritorio simple.

* Puede:

  * Abrir Google con una búsqueda:

    * “abrí Google y buscá Michael Jackson”.
  * Abrir YouTube con una búsqueda:

    * “abrí YouTube y buscá Escucho ofertas de Blender”.
  * Abrir el proyecto en VS Code, el directorio del repo, etc., según los comandos definidos en Desktop Agent.

* Cuando el LLM genera tool-calls `desktop_agent` dentro de bloques `json`, Lucy:

  * los detecta,
  * ejecuta las acciones permitidas,
  * limpia el JSON de la respuesta hablada,
  * y nunca rompe el nodo si hay errores de formato (usa fallback seguro).

* Es robusta frente a:

  * respuestas vacías del LLM,
  * TTS con texto vacío,
  * JSON mal formado (usa fallback y no se cae).

### 3.2. Lo que Lucy todavía NO hace

* **No navega dentro del navegador.**

  * Abre pestañas (Google/YouTube) con búsquedas listas.
  * **No** lee el DOM.
  * **No** elige resultados concretos.
  * **No** hace clic en “Play” ni controla el reproductor.

* **No existe todavía el Web Agent real.**

  * El módulo `lucy_web_agent` es sólo un esqueleto.
  * No hay integración de tool `web_agent` en el prompt del LLM ni en `app.py`.

* **Logging aún por pulir en la práctica.**

  * En código ya están las trazas para:

    * `STT text`,
    * input y output del LLM,
    * texto final hablado,
    * comandos de Desktop Agent.
  * Falta terminar de comprobar en ejecución real que siempre se ve en consola:

    * `You: ...`
    * `Assistant: ...`
    * y los `[LucyVoice]/[LucyDesktop]/[LucyVoiceActions]` coherentes en cada turno.

---

## 4. Problemas abiertos / frentes pendientes

1. **Logs “tipo caja negra” 100% confiables**

   * Objetivo: que para cada turno haya, como mínimo:

     * `STT text: ...`
     * `You: ...`
     * `get_llm_response input/raw/final ...`
     * `Assistant: ...`
     * `LucyVoiceActions` (si hubo plan)
     * `LucyDesktop` (comando y exit code)
   * Esto es vital para que, con un simple screenshot, el asistente del nuevo chat pueda reconstruir qué pasó.

2. **Experiencia específica con YouTube**

   * Hoy:

     * abre la búsqueda en YouTube bien,
     * pero no reproduce el video ni encuentra “el programa de hoy”.
   * El mensaje hablado ya aclara que no puede hacer clic, pero la expectativa del usuario es que, en el futuro, sí lo haga.

3. **Implementar el Web Agent (fase nueva)**

   * Elegir herramienta (Playwright/Selenium/etc.) 100% open source.
   * Implementar al menos:

     * `find_youtube_video_url` para:

       * buscar el canal correcto,
       * obtener el último video (o el vivo),
       * devolver la URL del video.
   * Integrarlo en `app.py` como tool `web_agent`, manteniendo:

     * seguridad,
     * separación de responsabilidades,
     * logs claros.

4. **Micro UX del ciclo de voz**

   * A veces confunde:

     * que hay que apretar **Enter** una vez para arrancar,
     * que `Ctrl+C` mata todo (y no deja ver ningún log).
   * Podría mejorarse el mensaje inicial para dejar esto más explícito.

---

## 5. Cómo seguir desde el próximo chat (guía para “la nueva IA”)

Cuando abras un nuevo chat dentro del proyecto y le pases:

* el link de GitHub,
* y este informe,

lo ideal es que el nuevo asistente haga esto:

1. **Leer (mentalmente) estos archivos del repo:**

   * `docs/LUCY-RESUMEN-TECNICO.md`
   * `docs/LUCY-DESKTOP-AGENT.md`
   * `docs/LUCY-WEB-AGENT-PLAN.md`
   * `lucy_agents/voice_actions.py`
   * `lucy_agents/desktop_bridge.py`
   * `scripts/lucy_desktop_agent.py`
   * `external/nodo-de-voz-modular-de-lucy/app.py`
   * `lucy_web_agent/youtube_agent.py`

2. **Probar el sistema con comandos concretos y logs:**

   En terminal:

   ```bash
   cd ~/Lucy_Workspace/Proyecto-VSCode
   ./scripts/lucy_voice_modular_node.sh
   ```

   * Apretar Enter cuando lo pida.

   * Probar, por ejemplo:

     1. “Hola Lucy, ¿cómo estás?”
     2. “Abrí Google y buscá Michael Jackson.”
     3. “Buscá Alejandro Dolina en YouTube y reproducilo.”

   * Verificar que en consola aparezcan los logs “You / Assistant / LucyVoice / LucyDesktop” por cada turno.

3. **Si los logs no están completos**, ajustar sólo eso primero (no tocar lógica nueva) hasta que:

   * cada turno deje una traza clara y compacta.

4. **Decidir el primer paso concreto del Web Agent**, siempre manteniendo:

   * todo local y open-source,
   * Desktop Agent como única pieza que toca OS,
   * Web Agent operando a nivel HTTP/navegador.

5. **Avanzar en “micro-pasos”** (como venimos haciendo):

   * un cambio a la vez,
   * comandos de consola claros,
   * commitear cada “músculo” nuevo con un mensaje legible.

---

Con esto queda el “handover” armado:
el nuevo chat sólo necesita este informe + el link al repo para seguir exactamente desde este punto, sin adivinar qué hicimos antes ni qué esperás que haga Lucy.   https://github.com/LokoKanishka/Proyecto-VSCode.githttps://github.com/LokoKanishka/Proyecto-VSCode.git

---

## Integración planificada de LoRA para GPT-OSS 20B

- Investigado y elegido el LoRA `YiwenX/gpt-oss-20b-multilingual-reasoner` (razonamiento multilingüe).
- Se mantiene `gpt-oss:20b` limpio y se planea un modelo fusionado aparte (`gpt-oss-20b-multireasoner`).
- Se añadió el script utilitario `tools/merge_gpt_oss_lora.py` para fusionar base + LoRA (no ejecutado aún).
- Pendiente: correr la fusión y exponer el modelo fusionado como alternativa de `llm_model` en Lucy Voz.
