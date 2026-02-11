#!/usr/bin/env python3
"""
Cartografía del IDE usando GridMapper híbrido

En lugar de pedir coordenadas exactas que el LLM no puede dar,
le pedimos que identifique REGIONES (grillas A1-H10) donde están
los elementos del IDE.

Esto es más confiable que bounding boxes precisos.
"""

import sys
import time
import pyautogui
import base64
import json
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

sys.path.append('.')

from src.skills.grid_mapper import GridMapper
from src.core.persistence import Hippocampus

# Configuración de la grilla
COLS = 8  # A-H
ROWS = 10  # 1-10


def draw_grid_overlay(screenshot):
    """Superpone una grilla visual sobre la captura de pantalla"""
    img = screenshot.copy()
    draw = ImageDraw.Draw(img)
    
    width, height = img.size
    cell_w = width / COLS
    cell_h = height / ROWS
    
    # Dibujar líneas verticales (columnas)
    for i in range(COLS + 1):
        x = int(i * cell_w)
        draw.line([(x, 0), (x, height)], fill='red', width=2)
        if i < COLS:
            # Etiqueta de columna
            label = chr(ord('A') + i)
            draw.text((x + cell_w//2 - 10, 10), label, fill='cyan')
    
    # Dibujar líneas horizontales (filas)
    for i in range(ROWS + 1):
        y = int(i * cell_h)
        draw.line([(0, y), (width, y)], fill='red', width=2)
        if i < ROWS:
            # Etiqueta de fila
            draw.text((10, y + cell_h//2 - 10), str(i + 1), fill='cyan')
    
    return img


def ask_vision_about_grid(grid_image_b64, element_description):
    """
    Pregunta al LLM de visión en qué celda de la grilla está un elemento.
    Esto es mucho más confiable que pedir coordenadas exactas.
    """
    
    prompt = f"""You are looking at a screenshot with a grid overlay (red lines, cyan labels).
Columns are labeled A-H, rows are labeled 1-10.

Find the '{element_description}' in this image.
Tell me which grid cell(s) it occupies. For example:
- If it's in one cell: {{"cell": "D5"}}
- If it spans multiple cells: {{"cells": ["C4", "D4", "E4"]}}
- If you can't find it: {{"error": "not found"}}

Respond ONLY with JSON. No explanation."""
    
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2-vision",
                "prompt": prompt,
                "images": [grid_image_b64],
                "stream": False,
                "format": "json"
            },
            timeout=60
        )
        
        if response.status_code != 200:
            print(f"❌ Vision API error: {response.status_code}")
            return None
        
        data = response.json()
        content = json.loads(data['response'])
        
        return content
        
    except Exception as e:
        print(f"⚡ Vision error: {e}")
        return None


def map_ide():
    """Cartografía del IDE usando visión + grillas"""
    
    memory = Hippocampus()
    
    print("\n🗺️ [LUCY] Iniciando Cartografía del IDE (Modo Grid Híbrido)")
    print("="*70)
    print("\n⚠️  Asegúrate de que VS Code esté:")
    print("   - Abierto y maximizado")
    print("   - Con la terminal visible (Ctrl+`)")
    print("   - Con el explorador de archivos visible (barra izquierda)")
    print("\nTienes 5 segundos para preparar la pantalla...\n")
    
    time.sleep(5)
    
    # Capturar pantalla
    print("📸 Capturando pantalla con grilla superpuesta...")
    screenshot = pyautogui.screenshot()
    
    # Dibujar grilla
    grid_screenshot = draw_grid_overlay(screenshot)
    
    # Guardar para debug
    grid_screenshot.save("/tmp/lucy_grid_view.png")
    print("💾 Grilla guardada en /tmp/lucy_grid_view.png (puedes verla si falla)")
    
    # Convertir a base64
    buffer = BytesIO()
    grid_screenshot.save(buffer, format="PNG")
    grid_b64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    # Zonas a mapear
    zones = {
        "terminal": "the integrated terminal panel at the bottom with command line text",
        "sidebar": "the file explorer sidebar on the left with folder tree",
        "editor": "the main code editor area in the center with text"
    }
    
    ide_map = {}
    
    for zone_name, description in zones.items():
        print(f"\n🔍 Buscando zona: {zone_name}...")
        
        result = ask_vision_about_grid(grid_b64, description)
        
        if result and "cell" in result:
            cell = result["cell"]
            print(f"   ✅ Encontrado en celda: {cell}")
            
            # Convertir celda a coordenadas
            coords = GridMapper.get_coordinates(cell)
            ide_map[zone_name] = {"cell": cell, "coords": coords}
            
            memory.save_thought(
                f"Zona IDE '{zone_name}' está en celda {cell} → coords {coords}",
                goal="Cartografía Workspace"
            )
            
        elif result and "cells" in result:
            cells = result["cells"]
            print(f"   ✅ Encontrado en celdas: {cells}")
            # Usar la primera celda como referencia
            cell = cells[0]
            coords = GridMapper.get_coordinates(cell)
            ide_map[zone_name] = {"cell": cell, "coords": coords, "span": cells}
            
        else:
            print(f"   ⚠️ No pude localizar '{zone_name}'")
    
    # Guardar mapa
    if ide_map:
        with open("ide_map.json", "w") as f:
            json.dump(ide_map, f, indent=2)
        
        print("\n" + "="*70)
        print(f"✅ Mapa guardado: {len(ide_map)}/3 zonas identificadas")
        print("\nMapa completo:")
        print(json.dumps(ide_map, indent=2))
        print("\n💾 Archivo: ide_map.json")
        print("="*70)
    else:
        print("\n❌ No se pudo mapear ninguna zona")


if __name__ == "__main__":
    map_ide()
