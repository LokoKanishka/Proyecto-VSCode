import re
from typing import Tuple

import pyautogui


class GridMapper:
    COLS = 8
    ROWS = 10

    @staticmethod
    def get_coordinates(grid_code: str) -> Tuple[int, int]:
        if not grid_code:
            raise ValueError("Grid code vacio")

        code = grid_code.strip().upper()
        match = re.match(r"^([A-Z])(\d{1,2})$", code)
        if not match:
            raise ValueError(f"Grid code invalido: {grid_code}")

        col_letter, row_str = match.groups()
        col_index = ord(col_letter) - ord("A")
        row_index = int(row_str) - 1

        if col_index < 0 or col_index >= GridMapper.COLS:
            raise ValueError(f"Columna fuera de rango: {col_letter}")
        if row_index < 0 or row_index >= GridMapper.ROWS:
            raise ValueError(f"Fila fuera de rango: {row_str}")

        screen_w, screen_h = pyautogui.size()
        cell_w = screen_w / GridMapper.COLS
        cell_h = screen_h / GridMapper.ROWS

        x = int((col_index + 0.5) * cell_w)
        y = int((row_index + 0.5) * cell_h)
        return x, y
