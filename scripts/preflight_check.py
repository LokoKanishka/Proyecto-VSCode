#!/usr/bin/env python3
"""
Pre-flight checks para Lucy Swarm.
Verificaciones rápidas antes de lanzar el swarm completo.
"""
import concurrent.futures
import sys
from pathlib import Path
from typing import Dict, Tuple


def check_syntax(file: Path) -> Tuple[str, bool]:
    """Verifica sintaxis de un archivo Python en paralelo."""
    import py_compile
    try:
        py_compile.compile(str(file), doraise=True)
        return (str(file.name), True)
    except py_compile.PyCompileError as e:
        return (str(file.name), False)


def check_ray_availability() -> bool:
    """Verifica si Ray está disponible (opcional)."""
    try:
        import ray
        return True
    except ImportError:
        return False


def check_file_exists(file: Path) -> Tuple[str, bool]:
    """Verifica que un archivo crítico exista."""
    return (str(file.name), file.exists())


def check_dependencies() -> Dict[str, bool]:
    """Verifica todas las dependencias críticas en paralelo."""
    checks = {}
    
    # Archivos críticos para swarm mode
    critical_files = [
        Path("src/engine/swarm_runner.py"),
        Path("src/core/manager.py"),
        Path("src/core/bus.py"),
        Path("src/memory/memory_manager.py"),
    ]
    
    # Verificación paralela de sintaxis
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        # Check de existencia (rápido)
        exist_futures = {executor.submit(check_file_exists, f): f for f in critical_files}
        for future in concurrent.futures.as_completed(exist_futures):
            name, exists = future.result()
            if not exists:
                checks[f"{name} (exists)"] = False
                continue
            
        # Check de sintaxis (más lento, solo si existen)
        syntax_futures = {executor.submit(check_syntax, f): f for f in critical_files if f.exists()}
        for future in concurrent.futures.as_completed(syntax_futures):
            name, ok = future.result()
            checks[f"{name} (syntax)"] = ok
    
    # Ray es opcional pero recomendado
    checks["ray (optional)"] = check_ray_availability()
    
    return checks


def main() -> int:
    """Ejecuta pre-flight checks y retorna código de salida."""
    print("🔍 Pre-flight checks...", end="", flush=True)
    
    results = check_dependencies()
    
    # Filtrar solo los críticos (no opcionales)
    critical_results = {k: v for k, v in results.items() if "optional" not in k}
    all_critical_ok = all(critical_results.values())
    
    if not all_critical_ok:
        print(" ❌")
        print("\n❌ Pre-flight checks failed:")
        for key, ok in results.items():
            if not ok and "optional" not in key:
                print(f"  - {key}")
        return 1
    
    print(" ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
