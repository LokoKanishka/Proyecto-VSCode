import os
from typing import List

import pyautogui
from PIL import Image, ImageDraw, ImageFont


class DesktopEye:
    def __init__(self, cols: int = 8, rows: int = 10):
        self.cols = cols
        self.rows = rows
        self.col_labels = self._build_col_labels(cols)

    def capture(self, overlay_grid: bool = True, out_path: str = "/tmp/lucy_vision.jpg") -> str:
        screenshot = pyautogui.screenshot()
        if overlay_grid:
            screenshot = self._apply_grid(screenshot)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        screenshot.convert("RGB").save(out_path, "JPEG", quality=90)
        return out_path

    def _apply_grid(self, image: Image.Image) -> Image.Image:
        base = image.convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        width, height = base.size
        cell_w = width / self.cols
        cell_h = height / self.rows

        # Vertical lines (red)
        for col in range(self.cols + 1):
            x = int(round(col * cell_w))
            draw.line([(x, 0), (x, height)], fill=(255, 0, 0, 120), width=2)

        # Horizontal lines (cyan)
        for row in range(self.rows + 1):
            y = int(round(row * cell_h))
            draw.line([(0, y), (width, y)], fill=(0, 255, 255, 120), width=2)

        font = ImageFont.load_default()
        padding_x, padding_y = 4, 2

        for row in range(self.rows):
            for col in range(self.cols):
                label = f"{self.col_labels[col]}{row + 1}"
                x = int(col * cell_w + padding_x)
                y = int(row * cell_h + padding_y)

                text_box = self._text_bbox(draw, label, font, x, y)
                draw.rectangle(
                    [
                        text_box[0] - 1,
                        text_box[1] - 1,
                        text_box[2] + 1,
                        text_box[3] + 1,
                    ],
                    fill=(0, 0, 0, 140),
                )
                draw.text((x, y), label, fill=(255, 255, 255, 220), font=font)

        return Image.alpha_composite(base, overlay)

    @staticmethod
    def _build_col_labels(cols: int) -> List[str]:
        return [chr(ord("A") + i) for i in range(cols)]

    @staticmethod
    def _text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, x: int, y: int):
        if hasattr(draw, "textbbox"):
            return draw.textbbox((x, y), text, font=font)
        text_w, text_h = draw.textsize(text, font=font)
        return (x, y, x + text_w, y + text_h)
