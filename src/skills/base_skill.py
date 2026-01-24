from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseSkill(ABC):
    """
    Clase base abstracta que todas las habilidades deben heredar.
    Garantiza que cada habilidad exponga su esquema para el LLM.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único de la herramienta para el LLM (ej: 'google_search')"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción en lenguaje natural de qué hace la herramienta."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """
        Esquema JSON (OpenAI-compatible) de los parámetros.
        Define qué argumentos necesita la función.
        """
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        La lógica de ejecución real.
        Debe devolver un string (o algo serializable a string)
        para ser inyectado de nuevo en el contexto del LLM.
        """
        pass
