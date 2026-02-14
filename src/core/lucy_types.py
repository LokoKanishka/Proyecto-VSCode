import uuid
import time
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class MessageType(str, Enum):
    COMMAND = "command"
    RESPONSE = "response"
    EVENT = "event"
    ERROR = "error"

class WorkerType(str, Enum):
    # Core
    MANAGER = "manager"
    # Senses
    EAR = "ear"        # Antes ear_worker
    MOUTH = "mouth"    # Antes mouth_worker
    VISION = "vision"  # Antes vision_worker
    HANDS = "hands"    # Antes hands_worker
    # Workers Cognitivos
    THOUGHT = "thought"
    MEMORY = "memory"
    SEARCH = "search_worker"
    CODE = "code_worker"
    SHELL = "shell_worker"
    # Legacy mappings (para compatibilidad temporal)
    LEGACY_EAR = "ear_worker"
    LEGACY_MOUTH = "mouth_worker"

class LucyMessage(BaseModel):
    """
    Estructura estándar de mensaje para el Bus de Enjambre.
    Ref: Plan Técnico - Sección 4 (Workers y Bus)
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    sender: str
    receiver: str  # 'broadcast' para eventos generales
    type: MessageType
    content: str  # Texto principal o instrucción
    data: Dict[str, Any] = Field(default_factory=dict)  # Payload estructurado (args, resultados)
    metadata: Dict[str, Any] = Field(default_factory=dict)  # Traceability, tokens, latency
    in_reply_to: Optional[str] = None
