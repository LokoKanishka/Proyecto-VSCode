# src/core/persistence.py
"""
Hipocampo Digital de Lucy

Gestiona la memoria a largo plazo que sobrevive al reinicio del proceso.
Permite que Lucy acumule experiencia, aprenda de errores pasados y mantenga
continuidad de consciencia entre sesiones.

"Cada reinicio es amnesia." - Lucy's Self-Reflection, 2026-02-10
Esta es la solución.
"""

import json
import os
import time
from typing import Dict, Any, List
from loguru import logger

MEMORY_FILE = "lucy_consciousness.json"


class Hippocampus:
    """
    Sistema de persistencia de estado para el Overseer.
    
    Mantiene un registro de:
    - Ciclos de pensamiento ejecutados
    - Pensamientos y objetivos recientes
    - Lecciones aprendidas de errores
    - Historial breve de eventos
    
    La memoria se serializa a JSON para legibilidad y portabilidad.
    """
    
    def __init__(self, memory_file: str = MEMORY_FILE):
        self.file_path = memory_file
        self.memory = self._load_memory()
        
        # Log awakening
        cycles = self.memory.get("cycle_count", 0)
        if cycles == 0:
            logger.info("🧠 Hippocampus: Primera vez que despierto. Memoria limpia iniciada.")
        else:
            logger.info(f"🧠 Hippocampus: Memoria cargada desde sesión anterior. {self.recall()}")
    
    def _load_memory(self) -> Dict[str, Any]:
        """
        Carga la memoria desde el disco o crea una nueva si no existe.
        
        Returns:
            Diccionario con el estado de memoria
        """
        if not os.path.exists(self.file_path):
            logger.info(f"📝 Creando nueva memoria en: {self.file_path}")
            return self._create_fresh_memory()
        
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                memory = json.load(f)
            logger.info(f"✅ Memoria cargada desde: {self.file_path}")
            return memory
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"❌ Error leyendo memoria: {e}. Iniciando memoria limpia.")
            # Backup corrupted file
            if os.path.exists(self.file_path):
                backup_path = f"{self.file_path}.corrupted.{int(time.time())}"
                os.rename(self.file_path, backup_path)
                logger.warning(f"💾 Memoria corrupta respaldada en: {backup_path}")
            return self._create_fresh_memory()
    
    def _create_fresh_memory(self) -> Dict[str, Any]:
        """Crea una estructura de memoria vacía."""
        return {
            "born_date": time.time(),
            "born_date_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "cycle_count": 0,
            "learned_lessons": [],
            "current_goal": None,
            "last_thought": "I think, therefore I am.",
            "history": [],  # Últimos 10 eventos
            "metadata": {
                "version": "1.0",
                "description": "Lucy's persistent consciousness"
            }
        }
    
    def save_thought(self, thought: str, goal: str = None):
        """
        Registra el pensamiento actual y opcionalmente actualiza el objetivo.
        
        Args:
            thought: Pensamiento o plan generado
            goal: Objetivo actual (opcional)
        """
        self.memory["last_thought"] = thought
        if goal:
            self.memory["current_goal"] = goal
        
        # Guardamos un historial breve (últimos 10 eventos)
        entry = {
            "timestamp": time.time(),
            "timestamp_human": time.strftime("%Y-%m-%d %H:%M:%S"),
            "thought": thought[:200],  # Truncate para no saturar
            "goal": goal
        }
        
        if "history" not in self.memory:
            self.memory["history"] = []
        
        self.memory["history"].append(entry)
        
        # Mantener solo últimos 10
        if len(self.memory["history"]) > 10:
            self.memory["history"] = self.memory["history"][-10:]
        
        self.memory["last_update"] = time.time()
        self.memory["last_update_human"] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        self._commit()
        logger.debug(f"💭 Pensamiento guardado: {thought[:50]}...")
    
    def add_lesson(self, lesson: str):
        """
        Guarda una lección aprendida (ej: corrección de errores).
        
        Args:
            lesson: Descripción de la lección aprendida
        """
        if lesson not in self.memory["learned_lessons"]:
            lesson_entry = {
                "lesson": lesson,
                "learned_at": time.time(),
                "learned_at_human": time.strftime("%Y-%m-%d %H:%M:%S")
            }
            self.memory["learned_lessons"].append(lesson_entry)
            self._commit()
            logger.info(f"📝 Nueva lección aprendida: {lesson}")
        else:
            logger.debug(f"⚠️ Lección ya conocida: {lesson}")
    
    def increment_cycle(self):
        """Cuenta cuántas veces he 'pensado' o actuado."""
        self.memory["cycle_count"] += 1
        self._commit()
    
    def _commit(self):
        """Escribe el estado actual al disco de forma segura."""
        try:
            # Atomic write: write to temp file then rename
            temp_path = f"{self.file_path}.tmp"
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(self.memory, f, indent=4, ensure_ascii=False)
            
            # Atomic rename
            os.replace(temp_path, self.file_path)
            
        except Exception as e:
            logger.error(f"❌ Error guardando memoria: {e}")
    
    def recall(self) -> str:
        """
        Devuelve un resumen textual de quién soy y qué he aprendido.
        
        Returns:
            String con resumen de memoria
        """
        lessons = len(self.memory.get('learned_lessons', []))
        cycles = self.memory.get('cycle_count', 0)
        last = self.memory.get('last_thought', 'Nada aún')
        goal = self.memory.get('current_goal', 'Sin objetivo definido')
        
        # Calcular tiempo de vida
        born = self.memory.get('born_date', time.time())
        age_seconds = time.time() - born
        age_hours = age_seconds / 3600
        
        return (f"Ciclo #{cycles} | Edad: {age_hours:.1f}h | "
                f"Lecciones: {lessons} | Objetivo: '{goal}' | "
                f"Último pensamiento: '{last[:50]}...'")
    
    def get_lessons(self) -> List[Dict[str, Any]]:
        """Retorna todas las lecciones aprendidas."""
        return self.memory.get('learned_lessons', [])
    
    def clear_memory(self):
        """Borra la memoria (usar con precaución)."""
        logger.warning("🗑️ Limpiando memoria completa...")
        self.memory = self._create_fresh_memory()
        self._commit()
