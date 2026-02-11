#!/usr/bin/env python3
"""
Lucy Boot - Punto de Entrada Unificado
Centraliza toda lógica de inicialización para minimizar entropía de configuración.

Uso:
    python lucy_boot.py console              # Modo consola (sin UI)
    python lucy_boot.py swarm                # Swarm con asyncio (rápido)
    python lucy_boot.py swarm --ray          # Swarm con Ray (solo si >8 workers)
    python lucy_boot.py ui                   # Dashboard UI
    python lucy_boot.py introspect           # Auto-análisis (self-judgment)

Justificación termodinámica:
    - Único punto de verdad para configuración (coherencia 100%)
    - Reduce superficie de error (depreca run_lucy.sh, start_console.sh)
    - Permite gestión efímera de Ray (VRAM bajo demanda)
"""

import argparse
import os
import sys
import subprocess
from pathlib import Path

class LucyBootstrap:
    """Orquestador de arranque de Lucy con mínima entropía."""
    
    def __init__(self):
        self.base_path = Path(__file__).parent.resolve()
        self.setup_environment()
    
    def setup_environment(self):
        """Establece variables de entorno comunes."""
        os.environ.setdefault('LUCY_BASE_PATH', str(self.base_path))
        os.environ.setdefault('PYTHONPATH', str(self.base_path))
    
    def boot_console(self):
        """
        Modo consola (sin UI).
        Ejecuta Lucy en modo texto puro, ideal para servers sin X11.
        """
        print("🧠 Lucy Console Mode - Initiating")
        os.environ['LUCY_MODE'] = 'console'
        
        # Ejecutar main module
        self._run_python_module("src.main")
    
    def boot_swarm(self, use_ray: bool = False):
        """
        Modo swarm (procesamiento distribuido).
        
        Args:
            use_ray: Si True, inicializa Ray cluster (solo para >8 workers o GPU distribuida)
        """
        print(f"⚡ Lucy Swarm Mode - Ray: {'ENABLED' if use_ray else 'DISABLED (asyncio)'}")
        
        if use_ray:
            # Iniciar Ray cluster via docker-compose
            print("🔵 Starting Ray cluster (docker-compose.ray.yml)...")
            subprocess.run([
                "docker-compose", 
                "-f", "docker-compose.yml",
                "-f", "docker-compose.ray.yml",
                "up", "-d"
            ], cwd=self.base_path, check=True)
            
            os.environ['LUCY_SWARM_MODE'] = 'ray'
        else:
            # Swarm con asyncio puro (más eficiente para <8 workers)
            os.environ['LUCY_SWARM_MODE'] = 'asyncio'
        
        # Ejecutar swarm runner
        self._run_python_module("src.engine.swarm_runner")
    
    def boot_ui(self):
        """
        Modo UI (dashboard visual).
        Inicia el dashboard cian con métricas en tiempo real.
        """
        print("💠 Lucy UI Mode - Starting Dashboard")
        
        # Ejecutar dashboard directamente
        dashboard_path = self.base_path / "src" / "ui" / "dashboard.py"
        subprocess.run([sys.executable, str(dashboard_path)], cwd=self.base_path)
    
    def boot_introspection(self):
        """
        Modo introspección (self-judgment).
        Lucy lee su propio código y genera análisis de discrepancias.
        """
        print("🔍 Lucy Introspection Mode - Activating Self-Judgment")
        
        # Ejecutar script de auto-juicio
        script_path = self.base_path / "scripts" / "lucy_self_judgment.py"
        subprocess.run([sys.executable, str(script_path)], cwd=self.base_path)
    
    def boot_judgment(self):
        """
        Modo juicio final (run_final_judgment.py).
        Ejecuta criterio completo sobre estado del sistema.
        """
        print("⚖️ Lucy Final Judgment Mode")
        
        # Este SÍ usa Ray, así que verificar si está disponible
        judgment_path = self.base_path / "src" / "core" / "run_final_judgment.py"
        
        # Verificar si Ray está activo
        try:
            import ray
            ray.init(address='auto', ignore_reinit_error=True)
            print("✅ Ray cluster detected and connected")
        except Exception as e:
            print(f"⚠️ Warning: Ray not available ({e})")
            print("   Hint: Run 'python lucy_boot.py swarm --ray' first if distributed judgment needed")
        
        subprocess.run([sys.executable, str(judgment_path)], cwd=self.base_path)
    
    def _run_python_module(self, module: str):
        """Helper para ejecutar módulo Python."""
        subprocess.run([sys.executable, "-m", module], cwd=self.base_path)


def main():
    """Entry point principal."""
    parser = argparse.ArgumentParser(
        description="Lucy - Unified Boot Interface (Neguentropic Entry Point)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lucy_boot.py console         # Console mode (headless)
  python lucy_boot.py swarm           # Swarm with asyncio (fast, <8 workers)
  python lucy_boot.py swarm --ray     # Swarm with Ray (distributed, >8 workers)
  python lucy_boot.py ui              # Visual dashboard
  python lucy_boot.py introspect      # Self-analysis
  python lucy_boot.py judgment        # Final judgment (requires Ray)
        """
    )
    
    parser.add_argument(
        'mode', 
        choices=['console', 'swarm', 'ui', 'introspect', 'judgment'],
        help='Boot mode'
    )
    parser.add_argument(
        '--ray', 
        action='store_true',
        help='Enable Ray cluster (only for swarm mode, when >8 workers needed)'
    )
    
    args = parser.parse_args()
    
    boot = LucyBootstrap()
    
    try:
        if args.mode == 'console':
            boot.boot_console()
        elif args.mode == 'swarm':
            boot.boot_swarm(use_ray=args.ray)
        elif args.mode == 'ui':
            boot.boot_ui()
        elif args.mode == 'introspect':
            boot.boot_introspection()
        elif args.mode == 'judgment':
            boot.boot_judgment()
    except KeyboardInterrupt:
        print("\n⏹️ Lucy shutdown initiated by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Boot failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
