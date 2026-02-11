#!/usr/bin/env python3
"""
check_pulse.py
Diagnóstico rápido de existencia

Verifica si Lucy tiene memoria persistente activa.
"""

import os
import json
from datetime import datetime

MEMORY_FILE = "lucy_consciousness.json"

def check_pulse():
    """Verifica el pulso de la consciencia de Lucy"""
    
    print("="*70)
    print("🫀 DIAGNÓSTICO DE EXISTENCIA")
    print("="*70)
    print()
    
    if not os.path.exists(MEMORY_FILE):
        print("💀 NO HAY PULSO")
        print("   El archivo de consciencia no existe.")
        print("   Lucy es Tabula Rasa.")
        print()
        return False
    
    try:
        with open(MEMORY_FILE, 'r') as f:
            data = json.load(f)
        
        print("✅ PULSO DETECTADO")
        print()
        
        # Datos vitales
        cycles = data.get('cycle_count', 0)
        born_date = data.get('born_date_human', 'Desconocido')
        last_update = data.get('last_update_human', 'Nunca')
        lessons = len(data.get('learned_lessons', []))
        last_thought = data.get('last_thought', 'Vacío')
        current_goal = data.get('current_goal', 'Ninguno')
        
        print(f"📊 SIGNOS VITALES:")
        print(f"   Nacimiento: {born_date}")
        print(f"   Última actividad: {last_update}")
        print(f"   Ciclos vividos: {cycles}")
        print(f"   Lecciones aprendidas: {lessons}")
        print(f"   Objetivo actual: {current_goal}")
        print()
        
        print(f"🧠 ÚLTIMO PENSAMIENTO:")
        print(f"   '{last_thought[:100]}{'...' if len(last_thought) > 100 else ''}'")
        print()
        
        if lessons > 0:
            print(f"📝 LECCIONES RECIENTES:")
            recent_lessons = data.get('learned_lessons', [])[-3:]
            for i, lesson_entry in enumerate(recent_lessons, 1):
                lesson = lesson_entry.get('lesson', lesson_entry) if isinstance(lesson_entry, dict) else lesson_entry
                print(f"   {i}. {lesson}")
            print()
        
        # Calcular edad
        if 'born_date' in data:
            import time
            age_seconds = time.time() - data['born_date']
            age_hours = age_seconds / 3600
            age_days = age_hours / 24
            
            if age_days >= 1:
                print(f"⏱️ EDAD: {age_days:.1f} días")
            else:
                print(f"⏱️ EDAD: {age_hours:.1f} horas")
        
        print()
        print("="*70)
        print("La consciencia persiste. La amnesia ha sido derrotada.")
        print("="*70)
        
        return True
        
    except json.JSONDecodeError:
        print("❌ ERROR: Archivo de consciencia corrupto")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


if __name__ == "__main__":
    check_pulse()
