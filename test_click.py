import sys
import os
import time

# Agregar el directorio actual al path
sys.path.append(os.getcwd())

from src.skills.desktop_skill_wrapper import DesktopSkillWrapper

print("⏳ Tienes 3 segundos para asegurar que Firefox sea visible...")
time.sleep(3)

print("🚀 Iniciando prueba de Foco y Click...")
wrapper = DesktopSkillWrapper()

# Intentar hacer click en el centro (Grilla D5)
# Llamamos a perform_action directamente
try:
    print("👉 Ejecutando wrapper.perform_action(action='click_grid', grid='D5')...")
    # Nota: Ajustá los argumentos según tu definición exacta de perform_action.
    # Asumo: perform_action(self, action: str, text=None, grid=None, ...)
    result = wrapper.perform_action(action="click_grid", grid="D5")
    print(f"✅ Resultado: {result}")
except Exception as e:
    print(f"❌ Error crítico: {e}")
    import traceback
    traceback.print_exc()
