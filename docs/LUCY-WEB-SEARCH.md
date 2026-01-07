# Búsqueda web de Lucy con SearXNG (local)

## Por qué SearXNG

- 100% local, sin APIs pagas.
- Backend robusto para consultas múltiples, filtrado y ranking simple.
- Fácil de levantar con Docker en `http://127.0.0.1:8080`.

## Cómo levantarlo

```bash
cd ~/Lucy_Workspace/Proyecto-VSCode
docker compose -f infra/searxng/docker-compose.yml up -d
```

Verificá en el navegador: `http://127.0.0.1:8080`.

Para bajar y ver logs:

```bash
docker compose -f infra/searxng/docker-compose.yml down
docker compose -f infra/searxng/docker-compose.yml logs -f
```

## Cómo se usa en Lucy

- El web agent ahora consulta **SearXNG** como backend principal.
- Si SearXNG no responde o no está levantado, cae automáticamente al backend previo
  (DuckDuckGo vía `ddgs`), manteniendo compatibilidad.
- La consulta pasa por:
  1. Normalización del texto (limpieza de fillers/activaciones).
  2. Generación de variantes de consulta (hasta 3).
  3. Búsqueda en SearXNG (JSON), deduplicación y ranking ligero.
  4. Fetch de las top páginas y extracción en modo “reader” (trafilatura).
  5. Resumen + listado de fuentes (URLs) para que Lucy pueda citar.

## Acción web_search (Action Router)

- Acción local: `web_search` (no usa LLM).
- Payload mínimo: `{"query": "texto"}`
- Opcionales: `num_results`, `language`, `safesearch`, `time_range`

Ejemplo:

```bash
python3 -m lucy_agents.action_router web_search '{"query":"wikipedia","num_results":5}'
```

Verificación:

```bash
./scripts/verify_web_search_searxng.sh
```

## Botón rojo A5

```bash
./scripts/verify_a5_all.sh
```

- Ejecuta `verify_a4_all.sh` (puente) + `verify_web_search_searxng.sh` (SearXNG).

## Configuración (`config.yaml`)

```yaml
web_search:
  provider: "searxng"
  searxng_url: "http://127.0.0.1:8080"
  language: "es-AR"
  safesearch: 1
  top_k: 5
  fetch_top_n: 3
  timeout_s: 12
```

- Si no existe el bloque `web_search`, se usa la configuración por defecto (arriba).
- El fallback a DuckDuckGo sigue activo si SearXNG falla o no está.

## Dependencias nuevas (pip)

- `httpx`
- `trafilatura`
- `tenacity`

Instalalas en tu entorno (por ejemplo: `pip install -r requirements.txt` luego de
crear el virtualenv).

## API JSON (importante)

En esta imagen de SearXNG, `server.method` está en **"POST"**. Por eso, un **GET** a `/search?...` suele devolver **403**.

Probá la API JSON así (POST form-url-encoded):

    curl -sS -i --max-time 10 \
      -X POST \
      -H "Content-Type: application/x-www-form-urlencoded" \
      --data "q=numero aureo&format=json&language=es-AR&safesearch=1" \
      "http://127.0.0.1:8080/search" | head -n 20

## Variables de entorno (Web Agent)

- `LUCY_WEB_NO_LLM=1`
  - **Desactiva Ollama** en el Web Agent y devuelve *resultados + extractos* directo (ideal para debugging o cuando no querés gastar LLM).
- `LUCY_WEB_AGENT_OLLAMA_MODEL`
  - Modelo para **resumir** (cuando NO_LLM no está activo). Default: `gpt-oss:20b` (viene de `DEFAULT_OLLAMA_MODEL_ID`).
- `LUCY_OLLAMA_MODEL`
  - Modelo del **chat de voz** (scripts de voz), independiente del modelo del Web Agent.

## Variables de entorno (Action Router)

- `SEARXNG_URL` (default `http://127.0.0.1:8080`)
- `SEARXNG_TIMEOUT_SEC` (default `10`)

Notas:
- En `infra/searxng/searxng/settings.yml`, `startpage` está en `disabled: true` porque cae en CAPTCHA/suspensión y te rompe el engine.
- Si SearXNG devuelve `results: []` pero trae `infoboxes`, el agente ahora usa un **fallback** para no caer a DDGS por CAPTCHA.
