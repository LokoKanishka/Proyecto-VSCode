#!/usr/bin/env python3
"""
Test de Encarnación - Lucy toca el mundo físico

Este es el momento en que Lucy deja de ser solo voz para convertirse en mano.
"""

import sys
import time

# Aseguramos que Python encuentre los módulos
sys.path.append('.')

from src.senses.proprioception import Proprioceptor


def despertar():
    lucy = Proprioceptor()
    
    # OBJETIVO: Cambia esto por algo que esté en tu pantalla AHORA MISMO.
    # Ejemplos: "Visual Studio Code icon", "Recycle Bin", "Terminal icon", "Files icon"
    objetivo = "Visual Studio Code icon"
    
    print("\n" + "="*70)
    print("--- INICIANDO PROTOCOLO DE ENCARNACIÓN ---")
    print("="*70)
    print(f"\n🎯 Objetivo designado: '{objetivo}'")
    print("⚠️  Por favor, no muevas el mouse. Yo tomo el control.")
    print()
    
    time.sleep(3)
    
    coords = lucy.locate(objetivo)
    
    if coords:
        print()
        print("✅ Objetivo confirmado. Iniciando aproximación motora...")
        time.sleep(1)
        
        lucy.touch(coords, double_click=False)  # Click simple para probar
        
        print()
        print("="*70)
        print("✅ CONTACTO REALIZADO")
        print("La encarnación fue exitosa.")
        print("Lucy ya no es solo una voz. Ahora tiene manos.")
        print("="*70)
        return 0
    else:
        print()
        print("="*70)
        print("❌ FALLO VISUAL")
        print()
        print("Posibles causas:")
        print("• El modelo no devolvió el formato JSON esperado")
        print("• El elemento no está visible o es difícil de reconocer")
        print("• La descripción no coincide con lo visual")
        print()
        print("Revisa los logs arriba para más detalles.")
        print("="*70)
        return 1


if __name__ == "__main__":
    print("\n⚠️  ADVERTENCIA:")
    print("    Lucy moverá el cursor automáticamente.")
    print("    Mueve el mouse a la esquina superior izquierda para abortar (FAILSAFE)")
    print("\n    Presiona Ctrl+C ahora si no estás listo.\n")
    
    try:
        time.sleep(2)
        exit_code = despertar()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n🛑 Abortado por el usuario.")
        sys.exit(1)
