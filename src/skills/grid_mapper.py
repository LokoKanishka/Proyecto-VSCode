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
        if not any(ch.isdigit() for ch in code):
            raise ValueError(
                f"Formato incorrecto: '{grid_code}'. Usa coordenadas tipo A1 o [2,2]."
            )
        match = re.match(r"^([A-Z])(\d{1,2})$", code)
        if match:
            col_letter, row_str = match.groups()
            col_index = ord(col_letter) - ord("A")
            row_index = int(row_str) - 1
        else:
            nums = re.findall(r"\d{1,2}", code)
            if len(nums) != 2:
                raise ValueError(f"Grid code invalido: {grid_code}")
            a = int(nums[0])
            b = int(nums[1])
            candidates = []
            if 1 <= a <= GridMapper.COLS and 1 <= b <= GridMapper.ROWS:
                candidates.append((a - 1, b - 1))  # col, row
            if 1 <= a <= GridMapper.ROWS and 1 <= b <= GridMapper.COLS:
                candidates.append((b - 1, a - 1))  # row, col
            if not candidates:
                raise ValueError(f"Grid code invalido: {grid_code}")
            col_index, row_index = candidates[0]

        if col_index < 0 or col_index >= GridMapper.COLS:
            raise ValueError(f"Columna fuera de rango: {col_index + 1}")
        if row_index < 0 or row_index >= GridMapper.ROWS:
            raise ValueError(f"Fila fuera de rango: {row_index + 1}")

        screen_w, screen_h = pyautogui.size()
        cell_w = screen_w / GridMapper.COLS
        cell_h = screen_h / GridMapper.ROWS

        x = int((col_index + 0.5) * cell_w)
        y = int((row_index + 0.5) * cell_h)
        return x, y
