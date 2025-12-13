# SearXNG local para Lucy

Instala una instancia **100% local** de SearXNG para mejorar la búsqueda web de Lucy.

## Requisitos

- Docker + Docker Compose
- Puerto `8080` libre

## Uso rápido

```bash
cd ~/Lucy_Workspace/Proyecto-VSCode
docker compose -f infra/searxng/docker-compose.yml up -d
```

Abrí `http://127.0.0.1:8080` en el navegador para verificar que la UI cargue.

### Bajar la instancia

```bash
docker compose -f infra/searxng/docker-compose.yml down
```

### Logs en vivo

```bash
docker compose -f infra/searxng/docker-compose.yml logs -f
```

## Notas

- La configuración por defecto es suficiente para el web agent. Si necesitás tunear
  `settings.yml`, copiá el archivo aquí y montalo con el volumen comentado en
  `docker-compose.yml`.
- Todo corre en local y sin APIs pagas. Si SearXNG no está levantado, el web agent
  hace fallback automático al backend anterior (DuckDuckGo / ddgs).

## API JSON (importante)

En esta imagen de SearXNG, `server.method` está en **"POST"**. Por eso, un **GET** a `/search?...` suele devolver **403**.

Probá la API JSON así (POST form-url-encoded):

    curl -sS -i --max-time 10 \
      -X POST \
      -H "Content-Type: application/x-www-form-urlencoded" \
      --data "q=numero aureo&format=json&language=es-AR&safesearch=1" \
      "http://127.0.0.1:8080/search" | head -n 20
