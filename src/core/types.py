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
    MANAGER = "manager"
    SEARCH = "search_worker"
    CHAT = "chat_worker"
    CODE = "code_worker"
    VISION = "vision_worker"
    EAR = "ear_worker"
    MOUTH = "mouth_worker"

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

class MemoryEntry(BaseModel):
    """Modelo para persistencia en SQLite/FAISS."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = Field(default_factory=time.time)
    role: str # user, assistant, system
    content: str
    session_id: str
    embedding: Optional[List[float]] = None # Vector para búsqueda semántica
    audio_path: Optional[str] = None
