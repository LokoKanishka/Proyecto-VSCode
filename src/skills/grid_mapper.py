"""
DEPRECATION NOTICE - Grid Mapper

Este módulo ha sido DEPRECADO en favor de src/vision/som_pipeline.py

Razón (Sección 5.1 del informe termodinámico):
    "Grid Mapping sufre de pérdida de traducción masiva:
     - Espacio de pantalla: 1920×1080 píxeles
     - Cuadrícula comprime a: ~100 celdas
     - LMMs alucinan frecuentemente en coordenadas numéricas precisas"

Reemplazo: Set-of-Mark (SoM)
    - Detección determinista con OpenCV
    - Etiquetado con IDs únicos sobre centroides
    - Click píxel-perfect (P_error < 5%)
    - Sin compresión espacial (resolución completa)

Migración:
    from src.vision.som_pipeline import get_som_pipeline
    
    som = get_som_pipeline()
    screenshot = capture_screen()
    marked_img, id_map = som.detect_and_mark(screenshot)
    x, y = som.click_by_id(target_id, id_map)

Fecha de deprecación: 2026-02-11
Eliminación planificada: v2.0
"""

import warnings
warnings.warn(
    "GridMapper is deprecated. Use SimpleSoMPipeline from src.vision.som_pipeline instead.",
    DeprecationWarning,
    stacklevel=2
)

# Original GridMapper code manteni do para backward compatibility
# (el código original sigue aquí pero genera warning)

class GridMapper:
    """DEPRECATED: Use SimpleSoMPipeline instead."""
    
    COLS = 8
    ROWS = 10
    
    @staticmethod
    def get_coordinates(cell_id: str) -> tuple:
        """
        DEPRECATED: Convierte celda (e.g., 'D5') a coordenadas.
        Use SoM Pipeline con IDs numéricos en su lugar.
        """
        warnings.warn(
            "GridMapper.get_coordinates() is deprecated. Use SoMPipeline.click_by_id()",
            DeprecationWarning
        )
        
        cell_id = cell_id.upper()
        col_char = cell_id[0]
        row_num = int(cell_id[1:])
        
        import pyautogui
        screen_width, screen_height = pyautogui.size()
        
        cell_width = screen_width / GridMapper.COLS
        cell_height = screen_height / GridMapper.ROWS
        
        col_index = ord(col_char) - ord('A')
        row_index = row_num - 1
        
        center_x = int((col_index + 0.5) * cell_width)
        center_y = int((row_index + 0.5) * cell_height)
        
        return (center_x, center_y)
