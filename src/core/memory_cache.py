"""
Synaptic Cache - Lucy's High-Speed Memory System
Hipocampo digital de alta velocidad para contexto de edición reciente.

Elimina el "Alzheimer digital" manteniendo en RAM:
- Archivos editados recientemente
- Hashes de contenido para detección de cambios
- Diffs incrementales
- Memoria espacial fusionada con contenido
"""
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
import difflib


@dataclass
class FileSnapshot:
    """Snapshot de un archivo en un momento específico."""
    path: str
    content: str
    content_hash: str
    timestamp: float
    line_count: int
    modified_lines: Set[int] = field(default_factory=set)
    
    @classmethod
    def from_file(cls, path: str, content: str) -> "FileSnapshot":
        """Crea snapshot desde contenido de archivo."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        line_count = len(content.splitlines())
        return cls(
            path=path,
            content=content,
            content_hash=content_hash,
            timestamp=time.time(),
            line_count=line_count,
        )
    
    def diff_lines(self, other: "FileSnapshot") -> Set[int]:
        """Calcula líneas modificadas entre snapshots."""
        if self.path != other.path:
            return set()
        
        old_lines = self.content.splitlines()
        new_lines = other.content.splitlines()
        
        diff = difflib.unified_diff(old_lines, new_lines, lineterm='')
        modified_lines = set()
        
        current_line = 0
        for line in diff:
            if line.startswith('@@'):
                # Parse line number from diff header
                parts = line.split()
                if len(parts) >= 3:
                    line_info = parts[2].lstrip('+').split(',')[0]
                    try:
                        current_line = int(line_info)
                    except ValueError:
                        pass
            elif line.startswith('+') and not line.startswith('+++'):
                modified_lines.add(current_line)
                current_line += 1
            elif line.startswith('-') and not line.startswith('---'):
                pass  # Deleted line
            else:
                current_line += 1
        
        return modified_lines


class SynapticCache:
    """
    Sistema de memoria de corto plazo para Lucy.
    Mantiene contexto reciente de archivos editados sin re-lectura de disco.
    """
    
    def __init__(self, max_files: int = 5, max_age_seconds: float = 300.0):
        """
        Args:
            max_files: Número máximo de archivos en cache
            max_age_seconds: Tiempo máximo de vida de un snapshot (default 5 min)
        """
        self.max_files = max_files
        self.max_age_seconds = max_age_seconds
        
        # OrderedDict para LRU behavior
        self._cache: OrderedDict[str, FileSnapshot] = OrderedDict()
        
        # Memoria espacial (fusión con ide_map)
        self._spatial_memory: Dict[str, dict] = {}
        
    def update(self, file_path: str, content: str) -> Optional[Set[int]]:
        """
        Actualiza cache con nuevo contenido de archivo.
        
        Returns:
            Set de líneas modificadas si el archivo ya estaba en cache, None si es nuevo
        """
        file_path = str(Path(file_path).resolve())
        
        new_snapshot = FileSnapshot.from_file(file_path, content)
        
        # Detectar cambios si ya existía
        modified_lines = None
        if file_path in self._cache:
            old_snapshot = self._cache[file_path]
            modified_lines = new_snapshot.diff_lines(old_snapshot)
            new_snapshot.modified_lines = modified_lines
        
        # Actualizar cache (mover al final si ya existía)
        if file_path in self._cache:
            del self._cache[file_path]
        
        self._cache[file_path] = new_snapshot
        
        # Eviction si excede max_files
        while len(self._cache) > self.max_files:
            self._cache.popitem(last=False)  # Remove oldest
        
        return modified_lines
    
    def get(self, file_path: str) -> Optional[FileSnapshot]:
        """Obtiene snapshot de archivo si está en cache y no expiró."""
        file_path = str(Path(file_path).resolve())
        
        if file_path not in self._cache:
            return None
        
        snapshot = self._cache[file_path]
        
        # Check expiration
        age = time.time() - snapshot.timestamp
        if age > self.max_age_seconds:
            del self._cache[file_path]
            return None
        
        # Move to end (LRU)
        self._cache.move_to_end(file_path)
        
        return snapshot
    
    def has_changed(self, file_path: str, content: str) -> bool:
        """Verifica si archivo cambió desde último snapshot."""
        snapshot = self.get(file_path)
        if not snapshot:
            return True  # No está en cache, asumimos cambio
        
        current_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return current_hash != snapshot.content_hash
    
    def get_recent_files(self) -> List[str]:
        """Retorna paths de archivos en cache (más reciente primero)."""
        return list(reversed(self._cache.keys()))
    
    def clear_expired(self):
        """Limpia snapshots expirados."""
        now = time.time()
        expired = [
            path for path, snap in self._cache.items()
            if (now - snap.timestamp) > self.max_age_seconds
        ]
        for path in expired:
            del self._cache[path]
    
    def update_spatial_memory(self, file_path: str, spatial_info: dict):
        """Fusiona memoria espacial (posición en IDE) con contenido."""
        file_path = str(Path(file_path).resolve())
        self._spatial_memory[file_path] = {
            'timestamp': time.time(),
            **spatial_info
        }
    
    def get_spatial_context(self, file_path: str) -> Optional[dict]:
        """Obtiene contexto espacial de archivo (posición en IDE, etc)."""
        file_path = str(Path(file_path).resolve())
        return self._spatial_memory.get(file_path)
    
    def get_contextual_summary(self) -> dict:
        """
        Genera resumen de contexto actual para respuestas instantáneas.
        
        Returns:
            Dict con archivos recientes, cambios, y memoria espacial
        """
        recent_files = self.get_recent_files()
        
        summary = {
            'recent_files': recent_files[:3],  # Top 3
            'total_cached': len(self._cache),
            'changes': {},
            'spatial_context': {}
        }
        
        for path in recent_files[:3]:
            snapshot = self._cache[path]
            summary['changes'][path] = {
                'modified_lines': list(snapshot.modified_lines),
                'line_count': snapshot.line_count,
                'age_seconds': time.time() - snapshot.timestamp
            }
            
            if path in self._spatial_memory:
                summary['spatial_context'][path] = self._spatial_memory[path]
        
        return summary
    
    def __len__(self) -> int:
        return len(self._cache)
    
    def __contains__(self, file_path: str) -> bool:
        return str(Path(file_path).resolve()) in self._cache


# Singleton global para uso en toda la aplicación
_global_cache: Optional[SynapticCache] = None


def get_synaptic_cache() -> SynapticCache:
    """Obtiene instancia global de Synaptic Cache."""
    global _global_cache
    if _global_cache is None:
        _global_cache = SynapticCache(max_files=5, max_age_seconds=300.0)
    return _global_cache


def reset_synaptic_cache():
    """Resetea cache global (útil para testing)."""
    global _global_cache
    _global_cache = None
