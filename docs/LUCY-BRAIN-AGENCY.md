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
