# Capa de "cerebro" de Lucy

Visión rápida de cómo piensa y actúa Lucy desde `external/nodo-de-voz-modular-de-lucy/app.py`.

## Qué es
- Nodo de voz modular: STT + VAD + TTS locales.
- LLM local (Ollama) con prompt de sistema que limita capacidades y herramientas.
- Agencia centrada en voz para escritorio, con resultados narrados en castellano rioplatense.

## Antes de llamar al LLM
- `lucy_agents.voice_actions` evalúa la frase y resuelve pedidos simples de escritorio (abrir Google/YouTube con búsqueda, etc.) usando Desktop Agent.
- Si `voice_actions` lo resuelve, no se llama al LLM.

## Herramientas que puede usar el LLM
- **desktop_agent**: abre apps/URLs o acciones simples de ventana a través del Desktop Agent.
  - Ejemplos de JSON:
    - `{"name":"desktop_agent","arguments":{"command":"xdg-open https://example.com"}}`
    - `{"name":"desktop_agent","arguments":{"url":"https://example.com"}}`
    - `{"name":"desktop_agent","arguments":{"action":"close_window","window_title":"YouTube"}}`
- **web_agent**: por ahora orientado a YouTube con yt-dlp.
  - Ejemplo:
    - `{"name":"web_agent","arguments":{"kind":"youtube_latest","query":"alejandro dolina","channel_hint":"eltrece"}}`
  - Si encuentra URL, la abre con Desktop Agent (`xdg-open <url>`).

## Convenciones de JSON para tool-calls
- `name`: `"desktop_agent"` o `"web_agent"`.
- `arguments`: diccionario con los campos anteriores.
- El JSON puede venir solo o dentro de bloques ```json ...```.
- Si la herramienta falla, la respuesta al usuario explica el fallo.

## Cómo se espera que crezca
- Más intents previos en `voice_actions` para ahorrar llamadas al LLM.
- Web agent con lectura de páginas, planeación en pasos y nuevas fuentes además de YouTube.
- Mejoras de robustez en parsing de tool-calls y logs para trazabilidad completa.

## Caso de uso: entrevistas de YouTube con reproducción automática

- Ejemplo de pedido: "Quiero que busques una entrevista en YouTube de Alejandro Dolina con Luis Navarro y que la reproduzcas."
- Flujo:
  1. `voice_actions` detecta que es un pedido complejo de YouTube (entrevista/programa + reproducir) y no arma ningún plan de escritorio; delega al LLM.
  2. El LLM genera un tool-call `web_agent`:
     ```json
     {
       "name": "web_agent",
       "arguments": {
         "kind": "youtube_latest",
         "query": "Alejandro Dolina Luis Navarro entrevista",
         "channel_hint": "Alejandro Dolina"
       }
     }
     ```
  3. `lucy_web_agent.youtube_agent` usa `yt-dlp` para buscar videos y elige uno:
     - Prioriza el canal sugerido por `channel_hint`, si coincide.
     - Si no, prioriza títulos con palabras como "entrevista", "programa", "capítulo".
     - Si ningún candidato es claro, devuelve una URL de búsqueda de YouTube con la query.
  4. El Web Agent devuelve la URL del video y `desktop_agent` ejecuta `xdg-open <url>`.
  5. El usuario luego puede pedir "Cerrá el navegador" o "cerrá YouTube" y el LLM puede usar:
     ```json
     {
       "name": "desktop_agent",
       "arguments": {
         "action": "close_window",
         "window_title": "YouTube"
       }
     }
     ```
- Logs visibles: `[LucyVoice] get_llm_response() input/raw/final`, `[LucyWebAgent] ...`, `[LucyDesktop] ...`.

## Entrevistas en YouTube con reproducción automática

- Detección de pedidos complejos:
  - Frases con YouTube (implícito u explícito) + contenido largo ("entrevista", "programa", "especial", "mano a mano", "charla", "capítulo") + verbo de reproducción ("poné", "reproducí", "dale play", etc.) se delegan al `web_agent`.
  - Si el usuario pide solo abrir/buscar sin reproducir ("solo abrí la búsqueda", "no la reproduzcas"), se usa el plan de escritorio simple con `xdg-open`.
- Elección de video en `youtube_agent`:
  - Normaliza y tokeniza quitando tildes y stopwords para comparar query, título y canal.
  - Puntúa candidatos priorizando coincidencias de tokens fuertes (nombres/keywords) y usa bonus por matches múltiples; si no hay coincidencias suficientes, cae al fallback de abrir la búsqueda.
- Criterio de decisión:
  - Si los tokens fuertes aparecen varias veces en título/canal, abre el video directo.
  - Si hay coincidencias débiles, solo abre búsqueda para que el usuario elija.
- Logs clave:
  - `[LucyVoiceActions] Pedido complejo de YouTube... se delega al LLM/web_agent.`
  - `[LucyWebAgent] Running yt-dlp ...`
  - `[LucyWebAgent] Puntajes candidatos: [...]`
  - `[LucyWebAgent] No hay candidato claro, devolviendo search_url genérica: ...`
  - `[LucyDesktop] Ejecutando comando: ['xdg-open', ...]`
