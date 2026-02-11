"""
Neural Watchdog - Lucy's Context Observer
Vigilancia de contexto en tiempo real para sincronización con Synaptic Cache.

Este proceso observa cambios en archivos críticos y actualiza automáticamente
la Synaptic Cache para que Lucy habite el código sin lag.
"""
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Dict, Set, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent
import yaml

try:
    from src.core.memory_cache import get_synaptic_cache
except ImportError:
    get_synaptic_cache = None


class ContextObserver(FileSystemEventHandler):
    """Observador de cambios en archivos para actualización de Synaptic Cache."""
    
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cache = get_synaptic_cache() if get_synaptic_cache else None
        self.last_seen: Dict[str, float] = {}
        self.debounce_interval = 0.5  # 500ms debounce
        
        # Archivos críticos a observar
        self.critical_patterns = {
            '*.py',
            '*.md',
            'config.yaml',
            'lucy_consciousness.json',
            'ide_map.json'
        }
        
    def on_modified(self, event):
        """Callback cuando un archivo es modificado."""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Filtrar solo archivos críticos
        if not self._is_critical(file_path):
            return
        
        # Debounce: evitar procesamiento múltiple del mismo evento
        now = time.time()
        path_str = str(file_path)
        if path_str in self.last_seen:
            if (now - self.last_seen[path_str]) < self.debounce_interval:
                return
        
        self.last_seen[path_str] = now
        
        # Actualizar Synaptic Cache
        self._update_cache(file_path)
    
    def _is_critical(self, path: Path) -> bool:
        """Verifica si el archivo es crítico para observación."""
        # Ignorar archivos en directorios específicos
        ignored_dirs = {'.git', '__pycache__', '.venv', 'node_modules', '.pytest_cache'}
        if any(part in ignored_dirs for part in path.parts):
            return False
        
        # Verificar extensiones críticas
        for pattern in self.critical_patterns:
            if path.match(pattern):
                return True
        
        return False
    
    def _update_cache(self, file_path: Path):
        """Actualiza Synaptic Cache con nuevo contenido de archivo."""
        if not self.cache:
            return
        
        try:
            # Leer contenido
            content = file_path.read_text(encoding='utf-8')
            
            # Actualizar cache
            modified_lines = self.cache.update(str(file_path), content)
            
            if modified_lines:
                print(f"💠 Cache updated: {file_path.name} ({len(modified_lines)} lines changed)")
            else:
                print(f"💠 Cache updated: {file_path.name} (new file)")
                
        except Exception as e:
            print(f"⚠️ Error updating cache for {file_path}: {e}")


class ConfigWatcher:
    """Observador específico de config.yaml para recalibración de recursos."""
    
    def __init__(self, config_path: Path):
        self.config_path = config_path
        self.last_hash = self._compute_hash()
    
    def _compute_hash(self) -> Optional[str]:
        """Calcula hash de config.yaml."""
        if not self.config_path.exists():
            return None
        try:
            content = self.config_path.read_bytes()
            return hashlib.sha256(content).hexdigest()[:16]
        except Exception:
            return None
    
    def check_for_changes(self) -> bool:
        """Verifica si config.yaml cambió."""
        current_hash = self._compute_hash()
        if current_hash != self.last_hash:
            self.last_hash = current_hash
            return True
        return False
    
    def get_resource_limits(self) -> dict:
        """Lee límites de recursos de config.yaml."""
        try:
            with open(self.config_path) as f:
                config = yaml.safe_load(f)
            
            return {
                'memory_limit': config.get('swarm', {}).get('memory_limit', '4GB'),
                'cpu_limit': config.get('swarm', {}).get('cpu_limit', 4),
                'worker_count': config.get('swarm', {}).get('worker_count', 8)
            }
        except Exception as e:
            print(f"⚠️ Error reading config: {e}")
            return {}


async def run_observer(project_root: str = "."):
    """
    Ejecuta el observador de contexto.
    
    Este proceso corre indefinidamente monitoreando cambios en archivos
    y sincronizando con Synaptic Cache.
    """
    project_path = Path(project_root).resolve()
    
    print("👁️ Neural Watchdog iniciado")
    print(f"📁 Observando: {project_path}")
    
    # Setup file observer
    context_observer = ContextObserver(project_path)
    observer = Observer()
    
    # Observar directorio src/
    src_path = project_path / "src"
    if src_path.exists():
        observer.schedule(context_observer, str(src_path), recursive=True)
        print(f"✅ Observando src/ recursivamente")
    
    # Observar archivos root críticos
    observer.schedule(context_observer, str(project_path), recursive=False)
    print(f"✅ Observando archivos root")
    
    # Setup config watcher
    config_watcher = ConfigWatcher(project_path / "config.yaml")
    
    # Start observer
    observer.start()
    
    try:
        while True:
            await asyncio.sleep(5)
            
            # Check config changes
            if config_watcher.check_for_changes():
                limits = config_watcher.get_resource_limits()
                print(f"⚙️ Config cambió: {limits}")
                
    except KeyboardInterrupt:
        print("\n🛑 Deteniendo Neural Watchdog...")
        observer.stop()
    
    observer.join()
    print("✅ Neural Watchdog detenido")


if __name__ == "__main__":
    asyncio.run(run_observer())
