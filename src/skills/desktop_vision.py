import os
import re
import shutil
import subprocess
from typing import List, Optional, Tuple

import pyautogui
from PIL import Image, ImageDraw, ImageFont


class DesktopEye:
    def __init__(self, cols: int = 8, rows: int = 10):
        self.cols = cols
        self.rows = rows
        self.col_labels = self._build_col_labels(cols)

    def capture(
        self,
        overlay_grid: bool = True,
        out_path: str = "/tmp/lucy_vision.jpg",
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> str:
        # Check if we are on Wayland
        is_wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY")
        
        if is_wayland:
            from src.vision.wayland_capture import WaylandCapture
            wc = WaylandCapture(output_dir=os.path.dirname(out_path))
            filename = os.path.basename(out_path)
            if region:
                x, y, w, h = region
                path = wc.capture_region(x, y, w, h, filename=filename)
            else:
                path = wc.capture_full(filename=filename)
            
            if path:
                screenshot = Image.open(path)
            else:
                # Fallback to pyautogui if grim fails
                screenshot = pyautogui.screenshot()
        else:
            region = region or self._active_window_region()
            if region:
                screenshot = pyautogui.screenshot(region=region)
            else:
                screenshot = pyautogui.screenshot()
                
        if overlay_grid:
            screenshot = self._apply_grid(screenshot)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        screenshot.convert("RGB").save(out_path, "JPEG", quality=90)
        return out_path

    def _active_window_region(self) -> Optional[Tuple[int, int, int, int]]:
        if os.environ.get("LUCY_CAPTURE_ACTIVE_WINDOW", "1") != "1":
            return None
        if not shutil.which("xdotool") or not shutil.which("xwininfo"):
            return None
        info = None
        try:
            win = None
            for cmd in (["xdotool", "getactivewindow"], ["xdotool", "getwindowfocus"]):
                try:
                    win = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                    if win:
                        break
                except Exception:
                    continue
            if win:
                info = subprocess.check_output(["xwininfo", "-id", win], text=True, stderr=subprocess.DEVNULL)
        except Exception:
            info = None

        if not info and shutil.which("wmctrl"):
            try:
                output = subprocess.check_output(["wmctrl", "-lx"], text=True, stderr=subprocess.DEVNULL)
                preferred = []
                fallback = []
                for line in output.splitlines():
                    lower = line.lower()
                    if "skyscanner" in lower:
                        preferred.append(line)
                    elif "firefox" in lower:
                        fallback.append(line)
                for line in preferred + fallback:
                    parts = line.split()
                    if not parts:
                        continue
                    win_id = parts[0]
                    try:
                        info = subprocess.check_output(
                            ["xwininfo", "-id", win_id],
                            text=True,
                            stderr=subprocess.DEVNULL,
                        )
                        if info:
                            break
                    except Exception:
                        continue
            except Exception:
                info = None

        if not info:
            return None

        def _search(pattern: str) -> Optional[int]:
            match = re.search(pattern, info)
            if not match:
                return None
            try:
                return int(match.group(1))
            except Exception:
                return None

        x = _search(r"Absolute upper-left X:\s+(-?\d+)")
        y = _search(r"Absolute upper-left Y:\s+(-?\d+)")
        width = _search(r"Width:\s+(\d+)")
        height = _search(r"Height:\s+(\d+)")
        if x is None or y is None or width is None or height is None:
            return None
        if width <= 0 or height <= 0:
            return None
        return (x, y, width, height)

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
