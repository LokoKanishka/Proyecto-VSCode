"""
src/core/memory_cache.py
Caché Sináptico - El Hipocampo de Alta Velocidad de Lucy.
"""
import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, Optional
import difflib

@dataclass
class FileSnapshot:
    """Instantánea de un archivo en el tiempo."""
    path: str
    content: str
    content_hash: str
    timestamp: float
    line_count: int
    modified_lines: Set[int] = field(default_factory=set)

    @classmethod
    def from_file(cls, path: str, content: str) -> "FileSnapshot":
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        return cls(
            path=path, content=content, content_hash=content_hash,
            timestamp=time.time(), line_count=len(content.splitlines())
        )

class SynapticCache:
    """
    Sistema de memoria de corto plazo. Mantiene el contexto de edición reciente.
    Evita la relectura constante de disco (entropía negativa).
    """
    def __init__(self, max_files: int = 10, max_age_seconds: float = 300.0):
        self.max_files = max_files
        self.max_age_seconds = max_age_seconds
        self._cache: OrderedDict = OrderedDict()

    def update(self, file_path: str, content: str) -> Optional[Set[int]]:
        """
        Actualiza el caché. Retorna las líneas modificadas si el archivo ya existía.
        Esto permite a los agentes de código enfocarse solo en lo nuevo (diffs).
        """
        file_path = str(Path(file_path).resolve())
        new_snap = FileSnapshot.from_file(file_path, content)
        
        modified_lines = None
        if file_path in self._cache:
            old_snap = self._cache[file_path]
            # Calculamos diff solo si el hash cambió
            if old_snap.content_hash != new_snap.content_hash:
                modified_lines = self._calculate_diff(old_snap.content, new_snap.content)
                new_snap.modified_lines = modified_lines
            else:
                modified_lines = set() # Sin cambios

        # Política LRU (Least Recently Used)
        if file_path in self._cache:
            del self._cache[file_path]
        self._cache[file_path] = new_snap
        
        while len(self._cache) > self.max_files:
            self._cache.popitem(last=False)
            
        return modified_lines

    def _calculate_diff(self, old: str, new: str) -> Set[int]:
        """Usa difflib para encontrar líneas cambiadas semánticamente."""
        diff = difflib.unified_diff(
            old.splitlines(), new.splitlines(), lineterm=''
        )
        changed = set()
        current_line = 0
        for line in diff:
            if line.startswith('@@'):
                # Parsear cabecera de diff @@ -x,y +a,b @@
                try:
                    parts = line.split() # +a,b
                    current_line = int(parts[2].lstrip('+').split(',')[0]) - 1
                except: pass
            elif line.startswith('+') and not line.startswith('+++'):
                changed.add(current_line)
                current_line += 1
            elif not line.startswith('-'):
                current_line += 1
        return changed

# Singleton global para acceso rápido desde cualquier worker
_global_cache = SynapticCache()
def get_synaptic_cache():
    return _global_cache
