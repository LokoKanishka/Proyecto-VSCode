# Lucy Web Agent — Plan de diseño

## 1. Objetivo

El **Lucy Web Agent** es un módulo separado cuya responsabilidad es:

- Navegar la web de forma más "humana":
  - abrir páginas,
  - leer contenido (HTML / DOM),
  - seguir algunos enlaces,
  - devolver resúmenes o URLs relevantes.

- Sincronizarse con la arquitectura actual:
  - **Mente**: LLM local (Ollama, gpt-oss:20b).
  - **Manos de escritorio**: Desktop Agent (xdg-open, code, nautilus, etc.).
  - **Web Agent**: una "mano" especializada en navegador, llamada explícitamente
    solo cuando Lucy necesita algo más que abrir una búsqueda.

## 2. Lo que NO es

- No reemplaza al Desktop Agent: éste sigue siendo el único que abre apps/URLs.
- No va a tener acceso irrestricto al sistema operativo (no borra archivos, etc.).
- No hace scraping masivo ni crawling loco: solo tareas puntuales, guiadas por Lucy.

## 3. Primer caso de uso: YouTube + “Escucho ofertas de Blender”

Caso concreto que disparó este módulo:

> “Abrí YouTube, buscá ‘Escucho ofertas de Blender’ y poné el programa de hoy.”

Descomposición deseada:

1. Web Agent recibe algo como:
   - `engine="youtube"`
   - `query="escucho ofertas de blender"`
   - `strategy="latest"` (por ahora, "el programa más reciente").
2. Abre (o controla) un navegador o un contexto de navegador:
   - busca en YouTube
   - filtra por canal si es posible (ej. canal oficial Blender).
3. Devuelve:
   - URL del video que debería reproducirse (ej. el último episodio).
4. Desktop Agent recibe esa URL y hace:
   - `xdg-open "https://www.youtube.com/watch?v=..."`.

Mientras tanto, Lucy dice algo honesto como:
> “Ya encontré el último programa de Escucho ofertas de Blender y te lo abrí en YouTube.”

## 4. API propuesta (Python)

Módulo sugerido: `lucy_web_agent/youtube_agent.py`

Funciones:

```python
from typing import Optional

def find_youtube_video_url(
    query: str,
    channel_hint: Optional[str] = None,
    strategy: str = "latest",
) -> Optional[str]:
    """
    Dado un texto de búsqueda y (opcionalmente) un identificador/dica de canal,
    intenta encontrar una URL de video de YouTube que encaje.

    Por ahora solo define la interfaz.
    La implementación real podrá usar Playwright, Selenium, o un cliente HTTP.

    Estrategias posibles:
    - "latest": el video más reciente que encaje con la búsqueda.
    - "live_or_latest": si hay vivo, usar ese; si no, el último video.

    Devuelve:
    - Una URL completa de YouTube (https://www.youtube.com/watch?v=...)
      si tuvo éxito.
    - None si no pudo encontrar nada aceptable.
    """
    raise NotImplementedError("Lucy Web Agent not implemented yet.")
```

## 5. Integración futura (borrador)

1. **Nuevo módulo Python**: `lucy_web_agent/youtube_agent.py` (como arriba).
2. **Nueva herramienta lógico-conceptual**: `web_agent` para el LLM:

   * El prompt de sistema le dirá a Lucy que, para tareas complejas de web,
     puede usar `web_agent` con argumentos (`engine`, `query`, `strategy`).
3. **Puente en app.py**:

   * Similar a cómo existe `desktop_agent`, habrá un manejador para JSON
     del tipo:

     ```json
     {
       "name": "web_agent",
       "arguments": {
         "engine": "youtube",
         "query": "escucho ofertas de blender",
         "strategy": "latest"
       }
     }
     ```
   * Este handler llamará a `find_youtube_video_url(...)`.
   * Si devuelve una URL, se la pasa al Desktop Agent como `xdg-open URL`.
4. **Seguridad**:

   * Las URLs generadas por el Web Agent siguen pasando por los filtros del
     Desktop Agent (https/http).
   * No se añade ninguna capacidad destructiva.

## 6. Fases

1. **Fase 0 (actual)**:

   * Lucy abre búsquedas en Google/YouTube.
   * Dice explícitamente que no puede hacer clic ni darle play.

2. **Fase 1 (plan actual)**:

   * Implementar `lucy_web_agent/youtube_agent.py` para el caso de uso
     YouTube + “Escucho ofertas de Blender”.
   * Integrarlo con un handler `web_agent` en app.py.
   * Probar y ajustar.

3. **Fase 2 (generalización)**:

   * Extender el Web Agent a otras consultas web (noticias, resúmenes
     de páginas, etc.).
   * Mantener siempre la separación:

     * LLM decide,
     * Web Agent navega/lee,
     * Desktop Agent abre URLs.

Con esto, el proyecto sigue siendo modular:

* mente (LLM),
* manos de escritorio (Desktop Agent),
* manos de navegador (Web Agent),
  y cada capa tiene responsabilidades claras.

