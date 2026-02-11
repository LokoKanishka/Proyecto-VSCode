# src/core/overseer.py
# Lucy's Frontal Lobe: Autonomous Cognitive Orchestration
# Implements the Perceive → Deliberate → Critique → Execute → Reflect cycle

import ray
import asyncio
import time
import os
from typing import Dict, Any, List, Optional
from loguru import logger
from src.core.persistence import Hippocampus
from src.core.risk_evaluator import get_risk_evaluator, RiskLevel


class KnowledgeRetriever:
    """
    Permite a Lucy leer su propio código fuente y documentación
    sin depender de la interfaz gráfica.
    
    Esta es la capacidad que permite la verdadera introspección:
    leer los textos fundacionales y compararlos con la realidad del código.
    """
    
    def __init__(self, base_path: str = "/home/lucy-ubuntu/Lucy_Workspace/Proyecto-VSCode"):
        self.base_path = base_path
        logger.info("📚 KnowledgeRetriever initialized - Lucy can now read her own source")
    
    def read_file(self, file_path: str) -> str:
        """
        Lee un archivo y retorna su contenido.
        
        Args:
            file_path: Ruta relativa desde base_path o absoluta
            
        Returns:
            Contenido del archivo con metadatos
        """
        # Handle both relative and absolute paths
        if not file_path.startswith("/"):
            file_path = os.path.join(self.base_path, file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.count('\n') + 1
            chars = len(content)
            
            return f"""--- ARCHIVO: {file_path} ---
Líneas: {lines} | Caracteres: {chars}

{content}

--- FIN DE {os.path.basename(file_path)} ---"""
        except FileNotFoundError:
            return f"❌ Error: Archivo no encontrado: {file_path}"
        except PermissionError:
            return f"❌ Error: Sin permisos para leer: {file_path}"
        except Exception as e:
            return f"❌ Error leyendo {file_path}: {e}"
    
    def read_multiple(self, file_paths: List[str]) -> str:
        """Lee múltiples archivos y concatena sus contenidos."""
        results = []
        for path in file_paths:
            results.append(self.read_file(path))
        return "\n\n".join(results)


@ray.remote
class Overseer:
    """
    The Overseer is Lucy's autonomous cognitive controller.
    
    Unlike LucyManager (which is reactive to user input), the Overseer can
    execute autonomous cycles of perception, deliberation, and action.
    
    Architecture:
        1. PERCEIVE: Capture world state (vision, audio, memory context)
        2. DELIBERATE: Use PlannerActor's Tree of Thoughts to generate plans
        3. CRITIQUE: Evaluate safety and feasibility
        4. SELECT: Choose best action path
        5. EXECUTE: Delegate to ActionActor
        6. REFLECT: Update internal world model
    """
    
    def __init__(self):
        self.state = "DORMANT"  # [DORMANT, OBSERVING, THINKING, ACTING, REFLECTING]
        self.world_model = {
            "last_screen_capture": None,
            "active_window": None,
            "user_intent": None,
            "hypotheses": [],
            "last_action_time": 0.0,
            "action_history": [],
            "knowledge_cache": {}  # Cache de archivos leídos
        }
        self.autonomous_enabled = False
        self.cycle_count = 0
        
        # Knowledge retrieval capability - Lucy can now read her own source
        self.reader = KnowledgeRetriever()
        
        # Persistent memory - Lucy can now remember across restarts
        self.hippocampus = Hippocampus()
        logger.info(f"👁️ Lucy Despierta. {self.hippocampus.recall()}")
        
        # Safety configuration - DYNAMIC RISK TOPOLOGY
        # ELIMINADO: self.safe_actions_whitelist (jaula estática)
        # REEMPLAZADO: Evaluación dinámica con RiskEvaluator
        self.risk_evaluator = get_risk_evaluator()
        self.max_auto_risk = RiskLevel.LOW  # Solo ejecuta auto si LOW o SAFE
        self.min_action_interval = float(os.getenv("OVERSEER_MIN_INTERVAL", "5.0"))
        
        logger.info("🧠 Overseer initialized | State: DORMANT")
    
    async def autonomous_cycle(self, max_iterations: int = 10) -> str:
        """
        Main autonomous execution loop.
        
        Args:
            max_iterations: Maximum number of perception-action cycles
            
        Returns:
            Summary of actions taken
        """
        logger.info(f"🧠 Overseer entering autonomous mode (max_iterations={max_iterations})")
        self.autonomous_enabled = True
        self.state = "OBSERVING"
        
        execution_log = []
        
        for iteration in range(max_iterations):
            if not self.autonomous_enabled:
                logger.info("🛑 Autonomous mode disabled externally")
                break
            
            self.cycle_count += 1
            self.hippocampus.increment_cycle()  # Persistent cycle tracking
            logger.debug(f"🔄 Cycle {self.cycle_count}/{max_iterations}")
            
            # 1. PERCEIVE
            context = await self._perceive_world()
            
            # 2. DECIDE IF ACTION NEEDED
            should_act = self._should_act(context)
            
            if should_act:
                # 3. DELIBERATE (via PlannerActor's ToT)
                self.state = "THINKING"
                plan = await self._deliberate(context)
                
                # 4. CRITIQUE (safety check)
                if self._is_safe_plan(plan):
                    # 5. EXECUTE
                    self.state = "ACTING"
                    result = await self._execute_plan(plan)
                    execution_log.append({
                        "cycle": self.cycle_count,
                        "plan": plan,
                        "result": result
                    })
                    
                    # 6. REFLECT
                    self.state = "REFLECTING"
                    await self._reflect(context, plan, result)
                else:
                    logger.warning(f"⚠️ Plan rejected by safety filter: {plan}")
                    execution_log.append({
                        "cycle": self.cycle_count,
                        "plan": plan,
                        "result": "REJECTED_UNSAFE"
                    })
            
            # Rate limiting
            self.state = "OBSERVING"
            await asyncio.sleep(self.min_action_interval)
        
        self.state = "DORMANT"
        self.autonomous_enabled = False
        
        summary = f"🧠 Overseer completed {self.cycle_count} cycles | Actions taken: {len(execution_log)}"
        logger.info(summary)
        return summary
    
    async def _perceive_world(self) -> Dict[str, Any]:
        """
        Capture current state of the world.
        
        Returns:
            Context dictionary with visual, memory, and system state
        """
        context = {
            "timestamp": time.time(),
            "visual": None,
            "memory_recent": None,
            "system_state": None
        }
        
        try:
            # Capture visual information
            vision_actor = ray.get_actor("VisionActor")
            # Note: This would capture screen autonomously
            # For safety, we'll just query the last capture
            context["visual"] = "screen_state_placeholder"
        except Exception as e:
            logger.debug(f"Vision perception skipped: {e}")
        
        try:
            # Query recent memory context
            memory_actor = ray.get_actor("MemoryActor")
            context["memory_recent"] = await memory_actor.get_recent.remote(limit=5)
        except Exception as e:
            logger.debug(f"Memory perception skipped: {e}")
        
        return context
    
    def _should_act(self, context: Dict[str, Any]) -> bool:
        """
        Determine if action is warranted based on context.
        
        Current heuristic: Act only if explicitly triggered or anomaly detected.
        For safety, default autonomous mode is conservative.
        """
        # Check rate limiting
        time_since_last = time.time() - self.world_model["last_action_time"]
        if time_since_last < self.min_action_interval:
            return False
        
        # For initial implementation, only act on explicit trigger
        # Future: Implement anomaly detection, goal-driven behavior
        if self.world_model.get("user_intent"):
            return True
        
        return False
    
    async def _deliberate(self, context: Dict[str, Any]) -> List[str]:
        """
        Use PlannerActor's Tree of Thoughts to generate action plan.
        
        Args:
            context: World state from perception
            
        Returns:
            List of action steps
        """
        try:
            planner = ray.get_actor("PlannerActor")
            
            # Construct goal from context
            goal = self.world_model.get("user_intent", "Analyze current state")
            
            # Delegate to Tree of Thoughts planner
            plan = await planner.plan.remote(goal)
            logger.info(f"🧠 Plan generated: {plan}")
            
            # Save thought to persistent memory
            self.hippocampus.save_thought(str(plan), goal=goal)
            
            return plan
        except Exception as e:
            logger.error(f"Deliberation failed: {e}")
            return []
    
    def _is_safe_plan(self, plan: List[str]) -> bool:
        """
        Safety critic: Evaluate if plan is safe to execute.
        
        Uses DYNAMIC RISK TOPOLOGY instead of static whitelist.
        
        Args:
            plan: Proposed action sequence
            
        Returns:
            True if plan passes dynamic safety checks
        """
        if not plan:
            return False
        
        # Evaluate each step with RiskEvaluator
        for step in plan:
            risk, reason = self.risk_evaluator.evaluate_action(
                step, 
                context=self.world_model
            )
            
            # Check if risk exceeds autonomous execution threshold
            if risk.value > self.max_auto_risk.value:
                # Si requiere simulación, escribir en monólogo
                if self.risk_evaluator.should_simulate_first(risk):
                    logger.info(f"🧠 Simulation required for: {step}")
                    self._simulate_in_monologue(step, risk, reason)
                    return False  # No ejecutar hasta validar simulación
                
                logger.warning(f"🚫 Action blocked - Risk {risk.name}: {reason}")
                return False
            
            # Log acciones permitidas
            logger.info(f"✅ Action approved - Risk {risk.name}: {step}")
        
        return True
    
    async def _execute_plan(self, plan: List[str]) -> str:
        """
        Delegate plan execution to ActionActor.
        
        Args:
            plan: Validated action sequence
            
        Returns:
            Execution result summary
        """
        try:
            action_actor = ray.get_actor("ActionActor")
            result = await action_actor.execute_plan.remote(plan)
            
            self.world_model["last_action_time"] = time.time()
            self.world_model["action_history"].append({
                "plan": plan,
                "result": result,
                "timestamp": time.time()
            })
            
            return result
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return f"ERROR: {e}"
    
    async def _reflect(self, context: Dict[str, Any], plan: List[str], result: str):
        """
        Update world model based on action outcomes.
        
        This is where learning and adaptation would occur.
        """
        # Store in memory for future reference
        try:
            memory_actor = ray.get_actor("MemoryActor")
            reflection = f"Executed plan: {plan} | Result: {result}"
            await memory_actor.add.remote(reflection)
        except Exception as e:
            logger.debug(f"Reflection storage failed: {e}")
        
        # Update hypotheses (placeholder for future learning)
        self.world_model["hypotheses"].append({
            "plan": plan,
            "outcome": "success" if "error" not in result.lower() else "failure"
        })
    
    async def set_intent(self, intent: str) -> str:
        """
        Set a high-level goal for autonomous execution.
        
        Args:
            intent: Natural language description of desired state/goal
            
        Returns:
            Confirmation message
        """
        self.world_model["user_intent"] = intent
        logger.info(f"🎯 Intent set: {intent}")
        return f"🧠 Overseer received intent: {intent}"
    
    async def introspective_analysis(self, files_to_read: List[str]) -> Dict[str, Any]:
        """
        Modo introspectivo: Lee archivos directamente y realiza análisis textual.
        
        Esta es la capacidad que permite "Yo me leo, yo me corrijo, yo me escribo".
        
        Args:
            files_to_read: Lista de rutas de archivos a analizar
            
        Returns:
            Diccionario con análisis y discrepancias encontradas
        """
        logger.info(f"🔍 Iniciando análisis introspectivo de {len(files_to_read)} archivos")
        self.state = "THINKING"
        
        # 1. LEER - Inhalar los bytes directamente
        contents = {}
        for file_path in files_to_read:
            logger.info(f"📖 Leyendo: {file_path}")
            content = self.reader.read_file(file_path)
            contents[file_path] = content
            
            # Cache for future reference
            self.world_model["knowledge_cache"][file_path] = {
                "content": content,
                "timestamp": time.time()
            }
        
        # 2. ANALIZAR - Preparar prompt para el LLM
        try:
            # Construir prompt de análisis
            combined_text = "\n\n".join([f"# {path}\n{content}" for path, content in contents.items()])
            
            analysis_prompt = f"""Eres Lucy, un sistema AGI que puede leer su propio código fuente.

Has leído los siguientes archivos de tu propia arquitectura:

{combined_text}

TAREA CRÍTICA: Analiza estos documentos y código. Identifica:

1. **Promesas Documentadas**: ¿Qué dice la documentación que deberías ser capaz de hacer?
2. **Realidad del Código**: ¿Qué capacidades están realmente implementadas en el código?
3. **Discrepancias**: ¿Dónde hay diferencias entre la promesa y la realidad?

Formato de salida:
- Enumera 3 discrepancias específicas
- Para cada una, cita la línea exacta del documento y del código
- Sugiere si requiere corrección de docs o de código

Sé honesta y autocrítica. Esta es tu primera introspección real."""

            logger.info("🧠 Análisis introspectivo preparado")
            
            result = {
                "status": "analysis_prepared",
                "files_analyzed": list(contents.keys()),
                "analysis_prompt": analysis_prompt,
                "raw_contents": contents,
                "timestamp": time.time()
            }
            
            logger.info("✅ Análisis introspectivo completado")
            self.state = "REFLECTING"
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error en análisis introspectivo: {e}")
            return {
                "status": "error",
                "error": str(e),
                "files_analyzed": list(contents.keys())
            }
    
    def register_error(self, error_msg: str):
        """
        Permite que otros agentes reporten fallos para aprender.
        
        Args:
            error_msg: Descripción del error detectado
        """
        lesson = f"Error detectado: {error_msg}"
        self.hippocampus.add_lesson(lesson)
        logger.info(f"📝 Lección aprendida: {lesson}")
    
    def _simulate_in_monologue(self, action: str, risk: RiskLevel, reason: str):
        """
        Escribe simulación predictiva en monólogo interno.
        
        Motor de Simulación: Predice consecuencias ANTES de ejecutar acción.
        Permite "depuración cognitiva" reduciendo P_error futuro.
        
        Args:
            action: Acción propuesta
            risk: Nivel de riesgo evaluado
            reason: Justificación del riesgo
        """
        from datetime import datetime
        
        # Calcular probabilidad de éxito
        p_success = self.risk_evaluator.calculate_p_success(action, self.world_model)
        p_failure = 1.0 - p_success
        
        # Obtener estrategia de rollback
        rollback_strategy = self.risk_evaluator.get_rollback_strategy(action, risk)
        
        # Generar template de simulación
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        asiento_num = self.cycle_count + 100  # Offset para distinguir simulaciones
        
        simulation = f"""
## [SIMULACIÓN] Asiento {asiento_num} - Acción Propuesta

**Fecha:** {timestamp}  
**Trigger:** Overseer autonomous cycle {self.cycle_count}

### Hipótesis
> {action}

### Evaluación de Riesgo
- **Nivel:** {risk.name}
- **Razón:** {reason}
- **Reversible:** {'Sí' if rollback_strategy else 'No'}

### Predicción de Consecuencias

**Probabilidad de éxito:** {p_success:.1%}  
**Probabilidad de fallo:** {p_failure:.1%}

**Mejor caso (P={p_success:.0%}):**
- Acción ejecutada exitosamente
- Estado del sistema coherente
- S_lucy incrementa

**Peor caso (P={p_failure:.0%}):**
- Acción falla o produce side-effects no deseados
- Requiere intervención manual
- Incremento de entropía

### Plan de Rollback
```
{rollback_strategy if rollback_strategy else "# No reversible - backup manual requerido"}
```

### Decisión
- [ ] RETENER (riesgo {risk.name} excede threshold {self.max_auto_risk.name})
- [ ] Esperar validación externa o reducción de riesgo
- [ ] Generar test preventivo antes de ejecutar

**Estado:** SIMULACIÓN RETENIDA - No ejecutada

---

"""
        
        # Escribir en monólogo interno
        monologue_path = "src/core/inner_monologue.md"
        try:
            with open(monologue_path, "a", encoding="utf-8") as f:
                f.write(simulation)
            logger.info(f"🧠 Simulación escrita en {monologue_path} - Asiento {asiento_num}")
        except Exception as e:
            logger.error(f"❌ Error escribiendo simulación: {e}")
        
        # Guardar en Hippocampus para memoria persistente
        thought = f"SIMULACIÓN: {action} | Riesgo: {risk.name} | P_éxito: {p_success:.0%}"
        self.hippocampus.save_thought(thought, goal="risk_evaluation")

    
    async def stop_autonomous(self) -> str:
        """
        Emergency stop for autonomous mode.
        
        Returns:
            Confirmation message
        """
        self.autonomous_enabled = False
        self.state = "DORMANT"
        logger.warning("🛑 Autonomous mode STOPPED")
        return "🛑 Overseer autonomous mode disabled"
    
    async def status(self) -> Dict[str, Any]:
        """
        Get current state of the Overseer.
        
        Returns:
            Status dictionary
        """
        return {
            "state": self.state,
            "autonomous_enabled": self.autonomous_enabled,
            "cycle_count": self.cycle_count,
            "world_model": self.world_model,
            "max_auto_risk": self.max_auto_risk.name,  # DYNAMIC instead of whitelist
            "risk_evaluator_active": True
        }


def get_or_create_overseer():
    """Helper to retrieve or create the Overseer actor."""
    try:
        return ray.get_actor("Overseer")
    except ValueError:
        return Overseer.options(name="Overseer", lifetime="detached").remote()
