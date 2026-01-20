from abc import ABC, abstractmethod
from typing import Generator

class AbstractEngine(ABC):
    """
    Abstract interface for AI engines (Local LLM, Mock, etc).
    """

    @abstractmethod
    def load_model(self, model_name: str) -> bool:
        """
        Loads a model by name. Returns True if successful.
        """
        pass

    @abstractmethod
    def generate_response(self, messages: list) -> Generator[str, None, None]:
        """
        Yields chunks of text (tokens) for streaming responses.
        messages: List of dicts [{"role": "user", "content": "..."}, ...]
        """
        pass
