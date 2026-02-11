"""
Set-of-Mark (SoM) Pipeline - Simplified Version
Visión determinista para clics precisos sin Grid Mapping.

Basado en Sección 5 del informe termodinámico:
    "El camino evolutivo correcto es la adopción de Set-of-Mark (SoM).
     Esta arquitectura desacopla la detección de la identificación."

Implementación simplificada sin YOLO:
    - Usa OpenCV para detección de contornos y componentes conectados
    - Etiquetado con IDs numéricos únicos
    - Click preciso en centroides (determinista, no probabilístico)
    
Ventajas vs Grid Mapping:
    1. Espacio completo: 1920×1080 píxeles (no comprimido a ~100 celdas)
    2. Sin alucinación: Detecta objetos reales, no adivina coordenadas
    3. Determinismo: Click en centroide exacto, P_error < 5%
"""

import cv2
import numpy as np
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from loguru import logger


class SimpleSoMPipeline:
    """
    Set-of-Mark pipeline simplificado usando OpenCV.
    
    Detección: Componentes conectados + contornos
    Etiquetado: IDs numéricos sobre centroides
    Acción: Click píxel-perfect en coordenadas exactas
    """
    
    def __init__(self, min_area: int = 500, max_objects: int = 100):
        """
        Args:
            min_area: Área mínima para considerar objeto (píxeles)
            max_objects: Máximo objetos a detectar (evitar ruido)
        """
        self.min_area = min_area
        self.max_objects = max_objects
        self.id_counter = 0
        logger.info(f"🎯 SimpleSoMPipeline initialized (min_area={min_area}, max={max_objects})")
    
    def detect_and_mark(self, screenshot: np.ndarray) -> Tuple[np.ndarray, Dict]:
        """
        Detecta objetos interactivos y genera imagen etiquetada.
        
        Args:
            screenshot: Imagen RGB (numpy array de cv2.imread o captura)
        
        Returns:
            (marked_image, id_map) donde:
                - marked_image: Screenshot con círculos y números ID
                - id_map: {id: {"coords": (x,y), "bbox": (x1,y1,x2,y2), ...}}
        """
        if screenshot is None or screenshot.size == 0:
            raise ValueError("Screenshot vacío o inválido")
        
        # Convertir a escala de grises para detección
        gray = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        
        # Aplicar threshold adaptativo para detectar elementos
        thresh = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Encontrar contornos (objetos potenciales)
        contours, _ = cv2.findContours(
            thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        
        # Filtrar por área y ordenar por tamaño (más grandes primero)
        valid_contours = [
            c for c in contours 
            if cv2.contourArea(c) >= self.min_area
        ]
        valid_contours.sort(key=cv2.contourArea, reverse=True)
        valid_contours = valid_contours[:self.max_objects]
        
        # Crear imagen marcada
        marked_img = screenshot.copy()
        id_map = {}
        
        for i, contour in enumerate(valid_contours):
            # Calcular bounding box
            x, y, w, h = cv2.boundingRect(contour)
            
            # Calcular centroide
            M = cv2.moments(contour)
            if M["m00"] == 0:
                continue  # Skip si no tiene área
            
            cx = int(M["m10"] / M["m00"])
            cy = int(M["m01"] / M["m00"])
            
            # Asignar ID único
            obj_id = self.id_counter
            self.id_counter += 1
            
            # Guardar en mapa
            id_map[obj_id] = {
                "coords": (cx, cy),
                "bbox": (x, y, x + w, y + h),
                "area": int(cv2.contourArea(contour)),
                "type": "detected_region"
            }
            
            # Dibujar en imagen marcada
            # Círculo amarillo en centroide
            cv2.circle(marked_img, (cx, cy), 20, (0, 255, 255), -1)
            
            # Número ID en negro sobre círculo
            cv2.putText(
                marked_img,
                str(obj_id),
                (cx - 8, cy + 8),  # Offset para centrar
                cv2.FONT_HERSHEY_BOLD,
                0.7,
                (0, 0, 0),
                2
            )
            
            # Bounding box en verde (opcional, para debug)
            if cv2.contourArea(contour) > self.min_area * 2:
                cv2.rectangle(marked_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
        
        logger.info(f"📍 Detected {len(id_map)} interactive regions")
        return marked_img, id_map
    
    def click_by_id(self, obj_id: int, id_map: Dict) -> Tuple[int, int]:
        """
        Retorna coordenadas exactas para click en objeto.
        
        Args:
            obj_id: ID del objeto (del mapa generado)
            id_map: Diccionario de objetos detectados
        
        Returns:
            (x, y) coordenadas píxel-perfect del centroide
        
        Raises:
            ValueError: Si ID no existe en mapa
        """
        if obj_id not in id_map:
            available = list(id_map.keys())
            raise ValueError(
                f"ID {obj_id} no encontrado. IDs disponibles: {available}"
            )
        
        x, y = id_map[obj_id]["coords"]
        logger.info(f"🎯 Click target: ID {obj_id} @ ({x}, {y})")
        return x, y
    
    def execute_click(self, obj_id: int, id_map: Dict):
        """
        Ejecuta click en objeto usando pyautogui.
        
        Args:
            obj_id: ID del objeto
            id_map: Mapa de objetos
        """
        try:
            import pyautogui
        except ImportError:
            logger.error("pyautogui no instalado - click no ejecutado")
            logger.info("Install: pip install pyautogui")
            return
        
        x, y = self.click_by_id(obj_id, id_map)
        pyautogui.click(x, y)
        logger.info(f"✅ Click ejecutado en ID {obj_id}: ({x}, {y})")
    
    def save_marked_image(self, marked_img: np.ndarray, path: str):
        """Guarda imagen marcada para visualización."""
        cv2.imwrite(path, marked_img)
        logger.info(f"💾 Marked image saved: {path}")
    
    def reset_counter(self):
        """Reinicia contador de IDs (útil para nueva sesión)."""
        self.id_counter = 0


def capture_screen() -> np.ndarray:
    """
    Captura screenshot usando toolkit disponible.
    
    Returns:
        numpy array RGB del screenshot
    """
    try:
        # Intento 1: mss (más rápido)
        from mss import mss
        with mss() as sct:
            monitor = sct.monitors[1]  # Primary monitor
            screenshot = sct.grab(monitor)
            img = np.array(screenshot)
            # Convertir BGRA a BGR
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            return img
    except ImportError:
        pass
    
    try:
        # Intento 2: PIL + ImageGrab
        from PIL import ImageGrab
        screenshot = ImageGrab.grab()
        img = np.array(screenshot)
        # Convertir RGB a BGR (opencv format)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img
    except ImportError:
        pass
    
    try:
        # Intento 3: pyautogui
        import pyautogui
        screenshot = pyautogui.screenshot()
        img = np.array(screenshot)
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        return img
    except ImportError:
        pass
    
    logger.error("❌ No screen capture library available (mss, PIL, pyautogui)")
    logger.info("Install one: pip install mss  OR  pip install pillow")
    return np.array([])


# Singleton instance
_som_pipeline = None

def get_som_pipeline(min_area: int = 500) -> SimpleSoMPipeline:
    """Obtiene instancia singleton del SoM pipeline."""
    global _som_pipeline
    if _som_pipeline is None:
        _som_pipeline = SimpleSoMPipeline(min_area=min_area)
    return _som_pipeline
