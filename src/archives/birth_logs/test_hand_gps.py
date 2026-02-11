from src.skills.grid_mapper import GridMapper
import pyautogui

print("Probando GPS de Mano...")
print(f"Resolucion: {pyautogui.size()}")

target = "C4"
pixels = GridMapper.get_coordinates(target)
print(f"Objetivo {target} -> {pixels}")

if pixels:
    pyautogui.moveTo(pixels[0], pixels[1], duration=1)
    print("Mouse movido.")
