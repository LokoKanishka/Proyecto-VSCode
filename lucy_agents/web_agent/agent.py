from __future__ import annotations

from typing import List, Optional

from smolagents import CodeAgent, DuckDuckGoSearchTool, LiteLLMModel


DEFAULT_OLLAMA_MODEL_ID = "ollama_chat/gpt-oss:20b"


def build_model(model_id: str = DEFAULT_OLLAMA_MODEL_ID) -> LiteLLMModel:
    """Construye el modelo LLM para el agente web.

    Por defecto usa un modelo local de Ollama a través de LiteLLM.
    Cambiá `model_id` si querés usar otro modelo de Ollama.
    """
    # Para Ollama no hace falta API key; LiteLLM usa la instalación local.
    return LiteLLMModel(model_id=model_id)


def build_agent(
    model_id: str = DEFAULT_OLLAMA_MODEL_ID,
    additional_imports: Optional[List[str]] | None = None,
    verbosity: int = 1,
) -> CodeAgent:
    """Crea un CodeAgent con herramientas de búsqueda web.

    - Usa DuckDuckGoSearchTool para buscar en la web.
    - Usa un modelo local de Ollama vía LiteLLM como "cerebro".
    """
    if additional_imports is None:
        additional_imports = [
            "math",
            "json",
            "datetime",
            "textwrap",
        ]

    model = build_model(model_id=model_id)
    search_tool = DuckDuckGoSearchTool()

    agent = CodeAgent(
        tools=[search_tool],
        model=model,
        add_base_tools=True,
        additional_authorized_imports=additional_imports,
        verbosity_level=verbosity,
    )
    return agent


def run_web_research(
    task: str,
    model_id: str = DEFAULT_OLLAMA_MODEL_ID,
    verbosity: int = 1,
) -> str:
    """Ejecuta una tarea de investigación web y devuelve la respuesta final.

    `task` debería describir claramente qué querés que haga Lucy, por ejemplo:
    - "Buscá noticias de hoy sobre inflación en Argentina y resumilas para un podcast"
    - "Compará reseñas recientes de monitores 1440p 27 pulgadas para gaming"
    """
    agent = build_agent(model_id=model_id, verbosity=verbosity)
    result = agent.run(task)

    # `agent.run` suele devolver directamente un string, pero por las dudas
    # soportamos generadores/streams.
    if isinstance(result, str):
        return result

    try:
        return "".join(str(chunk) for chunk in result)
    except TypeError:
        return str(result)
