"""
LUCY ALEPH VISION - Sistema de Percepción 'Hawk-Eye'.
Ubicación: src/core/vision_actor.py
"""
import ray
import mss
import mss.tools
import base64
import os
from loguru import logger
from typing import Dict, Any, Tuple

@ray.remote(num_gpus=0.2, namespace="lucy")
class VisionActor:
    def __init__(self):
        self.sct = mss.mss()
        self.monitor = self.sct.monitors[1] # Monitor principal
        self.grid_rows = 10
        self.grid_cols = 10
        logger.info("👁️ VISION ACTOR (Hawk-Eye) initialized.")

    async def capture_screen(self) -> Dict[str, Any]:
        """Captura la pantalla y retorna base64."""
        try:
            # Captura ultra-rápida con mss
            sct_img = self.sct.grab(self.monitor)
            
            # Convertir a PNG en memoria
            png = mss.tools.to_png(sct_img.rgb, sct_img.size)
            b64_str = base64.b64encode(png).decode('utf-8')
            
            return {
                "width": self.monitor["width"],
                "height": self.monitor["height"],
                "image_b64": b64_str,
                "timestamp": os.times().elapsed
            }
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"error": str(e)}

    async def grid_mapping(self, norm_x: str, norm_y: int) -> Tuple[int, int]:
        """
        Traduce coordenadas de grilla (A1-J10) a pixeles reales.
        Formato: 'A', 1 -> x, y
        """
        # A=0, B=1 ...
        col_idx = ord(norm_x.upper()) - 65
        row_idx = norm_y - 1
        
        if not (0 <= col_idx < self.grid_cols and 0 <= row_idx < self.grid_rows):
            return (0, 0)
            
        cell_w = self.monitor["width"] / self.grid_cols
        cell_h = self.monitor["height"] / self.grid_rows
        
        # Centro de la celda
        real_x = int((col_idx * cell_w) + (cell_w / 2)) + self.monitor["left"]
        real_y = int((row_idx * cell_h) + (cell_h / 2)) + self.monitor["top"]
        
        return (real_x, real_y)
