from __future__ import annotations

import base64
import logging
import math
import random
import time
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple, Union

import pyautogui
import shutil
import subprocess

np = None
try:
    import cv2
    import mss
    import numpy as np_
    np = np_
    HAS_SCREEN_LIBS = True
except ImportError:  # pragma: no cover - depende del entorno de ejecución
    HAS_SCREEN_LIBS = False

from src.skills.grid_mapper import GridMapper

logger = logging.getLogger(__name__)
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.04


@dataclass
class ScreenMetadata:
    width: int
    height: int
    grid_rows: int
    grid_cols: int
    cell_width: float
    cell_height: float
    timestamp: float
    region: Optional[Tuple[int, int, int, int]] = None


class ScreenState:
    """Captura de pantalla con grilla y apoyo visual."""

    def __init__(
        self,
        grid_rows: int = GridMapper.ROWS,
        grid_cols: int = GridMapper.COLS,
        monitor_idx: int = 1,
    ):
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.monitor_idx = monitor_idx
        if HAS_SCREEN_LIBS:
            self.sct = mss.mss()

    def capture_with_grid(
        self, overlay_grid: bool = True, region: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[str, ScreenMetadata]:
        if not HAS_SCREEN_LIBS:
            raise RuntimeError("Faltan librerías para capturar la pantalla.")
        img, metadata = self._grab(region)
        if overlay_grid:
            img = self._draw_grid(img)
        _, buffer = cv2.imencode(".jpg", img)
        img_b64 = base64.b64encode(buffer).decode("utf-8")
        return img_b64, metadata

    def capture_region(self, bbox: Tuple[int, int, int, int]) -> Optional[np.ndarray]:
        if not HAS_SCREEN_LIBS:
            return None
        img, _ = self._grab(bbox)
        return img

    def _grab(
        self, region: Optional[Tuple[int, int, int, int]] = None
    ) -> Tuple[np.ndarray, ScreenMetadata]:
        monitor = (
            self.sct.monitors[self.monitor_idx]
            if len(self.sct.monitors) > self.monitor_idx
            else self.sct.monitors[0]
        )
        if region:
            left, top, width, height = region
            grab = self.sct.grab({"left": left, "top": top, "width": width, "height": height})
        else:
            grab = self.sct.grab(monitor)
        img = cv2.cvtColor(np.array(grab), cv2.COLOR_BGRA2BGR)
        metadata = ScreenMetadata(
            width=img.shape[1],
            height=img.shape[0],
            grid_rows=self.grid_rows,
            grid_cols=self.grid_cols,
            cell_width=img.shape[1] / self.grid_cols,
            cell_height=img.shape[0] / self.grid_rows,
            timestamp=time.time(),
            region=region,
        )
        return img, metadata

    def _draw_grid(self, img: np.ndarray) -> np.ndarray:
        overlay = img.copy()
        dy = img.shape[0] / self.grid_rows
        dx = img.shape[1] / self.grid_cols
        color = (0, 255, 0)
        for i in range(1, self.grid_rows):
            y = int(dy * i)
            cv2.line(overlay, (0, y), (img.shape[1], y), color, 1)
        for j in range(1, self.grid_cols):
            x = int(dx * j)
            cv2.line(overlay, (x, 0), (x, img.shape[0]), color, 1)
        return cv2.addWeighted(img, 0.8, overlay, 0.2, 0)

    @staticmethod
    def region_difference(before: Optional[np.ndarray], after: Optional[np.ndarray]) -> float:
        if before is None or after is None:
            return 1.0
        if before.shape != after.shape:
            return 1.0
        diff = np.abs(before.astype(np.int16) - after.astype(np.int16))
        normalized = float(np.mean(diff)) / 255.0
        return normalized


class DesktopController:
    """Controlador de movimientos humanos y acciones seguras sobre la pantalla."""

    def __init__(self, verify_threshold: float = 0.02, duration: float = 0.6):
        self.screen_state = ScreenState()
        self.verify_threshold = verify_threshold
        self.default_duration = duration

    def compute_grid_coordinates(self, code: str) -> Tuple[int, int]:
        """Devuelve el centro de la celda, reutilizando GridMapper."""
        return GridMapper.get_coordinates(code)

    def compute_grid_bounds(self, code: str) -> Tuple[int, int, int, int]:
        return GridMapper.get_cell_bounds(code)

    def move_mouse_to_grid(
        self, code: str, duration: Optional[float] = None, jitter: bool = True
    ) -> None:
        x, y = self.compute_grid_coordinates(code)
        self._human_like_move(x, y, duration or self.default_duration, jitter)

    def click_grid_cell(
        self,
        code: str,
        button: str = "left",
        clicks: int = 1,
        interval: float = 0.2,
        verify: bool = True,
    ) -> bool:
        region = self.compute_grid_bounds(code)
        before = self.screen_state.capture_region(region) if verify else None
        x, y = self.compute_grid_coordinates(code)
        try:
            self._human_like_move(x, y, self.default_duration)
            pyautogui.click(button=button, clicks=clicks, interval=interval)
        except Exception:
            if not self._click_cli(x, y):
                raise
        after = self.screen_state.capture_region(region) if verify else None
        if verify:
            diff = ScreenState.region_difference(before, after)
            if diff < self.verify_threshold:
                logger.warning(
                    "📌 Verificación fallida en %s (diferencia %.3f).", code, diff
                )
            return diff >= self.verify_threshold
        return True

    def type_text(self, text: str, interval: float = 0.04):
        """Escribe texto simulando tipeo humano."""
        pyautogui.write(text, interval=interval)

    def press_hotkey(self, *keys: str):
        pyautogui.hotkey(*keys)

    def click_bbox(self, bbox: Tuple[int, int, int, int], verify: bool = True) -> bool:
        x, y, w, h = bbox
        cx = int(x + w / 2)
        cy = int(y + h / 2)
        before = self.screen_state.capture_region((x, y, w, h)) if verify else None
        try:
            self._human_like_move(cx, cy, self.default_duration)
            pyautogui.click()
        except Exception:
            if not self._click_cli(cx, cy):
                raise
        after = self.screen_state.capture_region((x, y, w, h)) if verify else None
        if verify:
            diff = ScreenState.region_difference(before, after)
            return diff >= self.verify_threshold
        return True

    def focus_window(self, title: str) -> bool:
        if not title:
            return False
        if shutil.which("wmctrl"):
            try:
                subprocess.run(["wmctrl", "-a", title], check=False)
                return True
            except Exception:
                return False
        if shutil.which("xdotool"):
            try:
                subprocess.run(["xdotool", "search", "--name", title, "windowactivate", "--sync"], check=False)
                return True
            except Exception:
                return False
        return False

    def _click_cli(self, x: int, y: int) -> bool:
        if shutil.which("xdotool"):
            try:
                subprocess.run(["xdotool", "mousemove", str(x), str(y), "click", "1"], check=False)
                return True
            except Exception:
                return False
        if shutil.which("ydotool"):
            try:
                subprocess.run(["ydotool", "mousemove", str(x), str(y)], check=False)
                subprocess.run(["ydotool", "click", "0xC0"], check=False)
                return True
            except Exception:
                return False
        return False

    def _human_like_move(
        self, x: int, y: int, duration: float, jitter: bool = True
    ) -> None:
        start_x, start_y = pyautogui.position()
        if start_x == x and start_y == y:
            return
        steps = max(6, int(duration * 60))
        for i in range(1, steps + 1):
            t = i / steps
            ease = 3 * t**2 - 2 * t**3
            target_x = start_x + (x - start_x) * ease
            target_y = start_y + (y - start_y) * ease
            if jitter:
                target_x += random.uniform(-1, 1)
                target_y += random.uniform(-1, 1)
            pyautogui.moveTo(int(target_x), int(target_y), duration=0)
            time.sleep(0.01)
        pyautogui.moveTo(x, y, duration=0)
