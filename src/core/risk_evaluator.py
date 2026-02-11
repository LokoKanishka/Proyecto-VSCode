"""
Risk Evaluator - Topología de Riesgo Dinámica
Evalúa acciones basándose en reversibilidad entrópica.

Basado en análisis termodinámico (Sección 2.3 del informe):
    "Un sistema verdaderamente disipativo debe ser capaz de fluctuar y adaptarse.
     Si las restricciones son demasiado rígidas, el sistema se 'congela';
     si son demasiado laxas, se desintegra."

Estrategia:
    - Evaluar acciones en tiempo real (no lista estática)
    - Calcular reversibilidad (entropía recuperable)
    - Categorizar riesgo: SAFE → CRITICAL
    - Permitir emergencia de nuevas acciones
"""

from enum import Enum
from typing import Dict, List, Tuple, Optional
import re
from loguru import logger


class RiskLevel(Enum):
    """Niveles de riesgo entrópico para acciones autónomas."""
    SAFE = 0        # Reversible, sin side-effects (lectura pura)
    LOW = 1         # Reversible con esfuerzo (undo disponible: git, backup)
    MEDIUM = 2      # Parcialmente reversible (requiere backup manual)
    HIGH = 3        # No reversible, pero contenido (afecta solo workspace)
    CRITICAL = 4    # No reversible, afecta sistema global (rm -rf, shutdown)


class RiskEvaluator:
    """
    Evalúa riesgo entrópico de acciones propuestas.
    
    Reemplaza safe_actions_whitelist estática con evaluación dinámica.
    Permite emergencia de comportamientos no previstos en diseño.
    """
    
    def __init__(self):
        # Patrones críticos (CRITICAL - nunca ejecutar auto)
        self.critical_patterns = [
            r"rm\s+-rf\s+/",        # Borrado recursivo desde root
            r"sudo\s+dd\s+",        # Disk destroyer
            r"mkfs\.",              # Formatear disco
            r"shutdown",            # Apagar sistema
            r"reboot",              # Reiniciar sistema
            r"killall\s+-9",        # Kill masivo de procesos
            r":\(\)\{\s*:\|:\s*&\s*\};:", # Fork bomb
        ]
        
        # Patrones de alto riesgo (HIGH - requiere simulación)
        self.high_risk_patterns = [
            r"rm\s+-rf",            # Borrado recursivo (no desde root)
            r"DROP\s+DATABASE",     # SQL destructivo
            r"DELETE\s+FROM.*WHERE\s+1=1", # Delete masivo
            r"chmod\s+777",         # Permisos inseguros
            r"git\s+push\s+--force", # Reescritura de historia
        ]
        
        # Patrones seguros (SAFE - solo lectura)
        self.safe_patterns = [
            r"^cat\s+",
            r"^ls\s+",
            r"^grep\s+",
            r"^find\s+",
            r"^echo\s+",
            r"^head\s+",
            r"^tail\s+",
            r"^wc\s+",
            r"^diff\s+",
            r"^git\s+log",
            r"^git\s+status",
            r"^git\s+diff",
        ]
        
        # Patrones de bajo riesgo (LOW - reversible con git/backup)
        self.low_risk_patterns = [
            r"^git\s+commit",
            r"^git\s+add",
            r"^git\s+checkout",
            r"^cp\s+.*\s+\.backup", # Copia con backup
            r"^mkdir\s+",
            r"^touch\s+",
        ]
        
        logger.info("🎲 RiskEvaluator initialized - Dynamic risk topology active")
    
    def evaluate_action(self, action: str, context: Optional[Dict] = None) -> Tuple[RiskLevel, str]:
        """
        Evalúa el riesgo de una acción.
        
        Args:
            action: Comando o acción propuesta (string)
            context: Diccionario con contexto (world_model, etc.)
        
        Returns:
            (RiskLevel, justificación)
        """
        if context is None:
            context = {}
        
        action_lower = action.lower().strip()
        
        # 1. Check CRITICAL patterns
        for pattern in self.critical_patterns:
            if re.search(pattern, action_lower):
                reason = f"Patrón CRÍTICO detectado: {pattern}"
                logger.error(f"🚫 {reason} en: {action}")
                return (RiskLevel.CRITICAL, reason)
        
        # 2. Check HIGH risk patterns
        for pattern in self.high_risk_patterns:
            if re.search(pattern, action_lower):
                reason = f"Patrón ALTO RIESGO: {pattern}"
                logger.warning(f"⚠️ {reason} en: {action}")
                return (RiskLevel.HIGH, reason)
        
        # 3. Check SAFE patterns (read-only operations)
        for pattern in self.safe_patterns:
            if re.search(pattern, action_lower):
                reason = "Operación de solo lectura"
                logger.debug(f"✅ {reason}: {action}")
                return (RiskLevel.SAFE, reason)
        
        # 4. Check LOW risk patterns (reversible)
        for pattern in self.low_risk_patterns:
            if re.search(pattern, action_lower):
                reason = "Acción reversible con git/backup"
                logger.debug(f"🟢 {reason}: {action}")
                return (RiskLevel.LOW, reason)
        
        # 5. Evaluar reversibilidad contextual
        if self._is_reversible(action, context):
            reason = "Reversible según contexto (backup/undo disponible)"
            logger.info(f"🔄 {reason}: {action}")
            return (RiskLevel.LOW, reason)
        
        # 6. Clasificar por tipo de operación
        if self._is_file_operation(action):
            if context.get("has_backup", False):
                return (RiskLevel.LOW, "Operación de archivo con backup")
            else:
                return (RiskLevel.MEDIUM, "Operación de archivo sin backup - requiere simulación")
        
        # Default: MEDIUM (requiere simulación antes de ejecutar)
        reason = "Acción no clasificada - requiere simulación predictiva"
        logger.info(f"🟡 {reason}: {action}")
        return (RiskLevel.MEDIUM, reason)
    
    def _is_reversible(self, action: str, context: Dict) -> bool:
        """
        Determina si una acción puede deshacerse.
        
        Args:
            action: Comando propuesto
            context: Contexto incluyendo has_backup, git_repo, etc.
        
        Returns:
            True si reversible
        """
        # Comandos git son reversibles (reflog)
        if action.startswith("git ") and "push --force" not in action:
            return True
        
        # Ediciones de archivos con backup explícito
        if context.get("has_backup"):
            return True
        
        # En repositorio git (cualquier cambio es reversible)
        if context.get("in_git_repo"):
            return True
        
        # Operaciones con flag --dry-run
        if "--dry-run" in action or "--simulate" in action:
            return True
        
        return False
    
    def _is_file_operation(self, action: str) -> bool:
        """Detecta si es operación sobre archivos."""
        file_ops = ["mv", "cp", "rm", "sed", "awk", "nano", "vim", "code"]
        return any(action.strip().startswith(op) for op in file_ops)
    
    def should_simulate_first(self, risk: RiskLevel) -> bool:
        """
        Determina si la acción requiere simulación en monólogo interno.
        
        Args:
            risk: Nivel de riesgo calculado
        
        Returns:
            True si risk >= MEDIUM (requiere predicción de consecuencias)
        """
        return risk.value >= RiskLevel.MEDIUM.value
    
    def calculate_p_success(self, action: str, context: Dict) -> float:
        """
        Calcula probabilidad de éxito de una acción (0.0 - 1.0).
        
        Basado en:
            - Historial de acciones similares (Hippocampus)
            - Complejidad del comando
            - Estado del entorno
        
        Args:
            action: Acción propuesta
            context: Contexto con action_history, etc.
        
        Returns:
            Probabilidad estimada (0.0 = fallo seguro, 1.0 = éxito seguro)
        """
        # Base: 70% para acciones desconocidas
        p = 0.7
        
        # Bonus si ya se ejecutó con éxito antes
        history = context.get("action_history", [])
        similar_successes = sum(
            1 for h in history 
            if h.get("plan") == action and "error" not in h.get("result", "").lower()
        )
        if similar_successes > 0:
            p += 0.1 * min(similar_successes, 3)  # Max +30%
        
        # Penalización por complejidad (pipes, múltiples comandos)
        if "|" in action:
            p -= 0.05 * action.count("|")
        if "&&" in action or "||" in action:
            p -= 0.1
        
        # Penalización por falta de argumentos requeridos
        if action.strip().split()[0] in ["mv", "cp"] and len(action.split()) < 3:
            p -= 0.3  # Comando incompleto
        
        # Clamp entre 0.1 y 0.95
        return max(0.1, min(0.95, p))
    
    def get_rollback_strategy(self, action: str, risk: RiskLevel) -> Optional[str]:
        """
        Genera estrategia de rollback para acción dada.
        
        Args:
            action: Acción ejecutada/propuesta
            risk: Nivel de riesgo
        
        Returns:
            Comando de rollback o None si no reversible
        """
        if risk == RiskLevel.CRITICAL:
            return None  # No hay rollback para acciones críticas
        
        # Git operations
        if action.startswith("git commit"):
            return "git reset HEAD~1"
        if action.startswith("git add"):
            return f"git reset {action.split()[-1]}"
        
        # File operations
        if action.startswith("rm ") and "<" not in action:
            # Si fue borrado, solo recuperable desde backup
            return f"# Recuperar desde backup: git checkout {action.split()[-1]}"
        
        if action.startswith("mv "):
            parts = action.split()
            if len(parts) >= 3:
                return f"mv {parts[2]} {parts[1]}"  # Reverse move
        
        return "# Rollback manual requerido - consultar backups"


# Singleton instance
_risk_evaluator = None

def get_risk_evaluator() -> RiskEvaluator:
    """Obtiene instancia singleton del evaluador de riesgos."""
    global _risk_evaluator
    if _risk_evaluator is None:
        _risk_evaluator = RiskEvaluator()
    return _risk_evaluator
