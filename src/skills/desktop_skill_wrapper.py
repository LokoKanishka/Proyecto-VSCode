import json
import os
import re
import subprocess
import time
from shutil import which
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import pyautogui
from loguru import logger

from src.skills.base_skill import BaseSkill
from src.skills.desktop_action import DesktopHand
from src.skills.desktop_vision import DesktopEye
from src.skills.grid_mapper import GridMapper

_LAST_APP_NAME: Optional[str] = None


def _set_last_app(name: Optional[str]) -> None:
    global _LAST_APP_NAME
    if not name:
        return
    _LAST_APP_NAME = str(name).strip().lower() or _LAST_APP_NAME


def _get_last_app() -> Optional[str]:
    return _LAST_APP_NAME


class DesktopVisionSkill(BaseSkill):
    def __init__(self, eye: Optional[DesktopEye] = None):
        self._eye = eye or DesktopEye()
        self._last_focus_attempt = 0.0

    def _log_active_window(self) -> None:
        if which("xdotool") is None:
            return
        try:
            win = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if not win:
                return
            title = ""
            try:
                title = subprocess.check_output(
                    ["xdotool", "getwindowname", win],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except Exception:
                title = ""
            logger.info("🪟 Ventana activa: {} {}", win, f"'{title}'" if title else "")
        except Exception:
            return

    def _get_active_window_title(self) -> str:
        if which("xdotool") is None:
            return ""
        try:
            win = subprocess.check_output(
                ["xdotool", "getactivewindow"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
            if not win:
                return ""
            return subprocess.check_output(
                ["xdotool", "getwindowname", win],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except Exception:
            return ""

    def _active_window_region(self) -> Optional[tuple[int, int, int, int]]:
        if which("xwininfo") is None:
            return None
        win_id = None
        if which("xdotool") is not None:
            for cmd in (["xdotool", "getactivewindow"], ["xdotool", "getwindowfocus"]):
                try:
                    win_id = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                    if win_id:
                        break
                except Exception:
                    continue
        if not win_id and which("wmctrl") is not None:
            try:
                output = subprocess.check_output(["wmctrl", "-lx"], text=True, stderr=subprocess.DEVNULL)
                for line in output.splitlines():
                    lower = line.lower()
                    if (
                        "skyscanner" in lower
                        or "firefox" in lower
                        or "chrome" in lower
                        or "chromium" in lower
                    ):
                        win_id = line.split()[0]
                        break
            except Exception:
                win_id = None
        if not win_id:
            return None
        try:
            info = subprocess.check_output(["xwininfo", "-id", win_id], text=True, stderr=subprocess.DEVNULL)
        except Exception:
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

    def _focus_target_window(self) -> None:
        target = os.environ.get("LUCY_FOCUS_APP") or _get_last_app()
        if not target:
            if which("google-chrome") is not None:
                target = "google-chrome"
            elif which("chromium") is not None:
                target = "chromium"
            else:
                target = "firefox"
        target = str(target).strip()
        if not target:
            return
        # Avoid hammering focus every time in tight loops.
        now = time.time()
        if now - self._last_focus_attempt < 0.4:
            return
        self._last_focus_attempt = now

        class_candidates = [target]
        name_candidates = [target]
        if target.lower() == "firefox":
            class_candidates.extend(["firefox", "Navigator", "navigator"])
            name_candidates.extend(["Firefox", "Mozilla Firefox"])
        if target.lower() in {"google-chrome", "chrome", "chromium"}:
            class_candidates.extend(["google-chrome", "Google-chrome", "chromium", "Chromium"])
            name_candidates.extend(["Google Chrome", "Chrome", "Chromium"])

        seen = set()
        class_candidates = [c for c in class_candidates if c and not (c in seen or seen.add(c))]
        seen = set()
        name_candidates = [c for c in name_candidates if c and not (c in seen or seen.add(c))]

        def _try_focus_once() -> bool:
            if target.lower() == "firefox":
                if which("wmctrl") is not None:
                    try:
                        output = subprocess.check_output(
                            ["wmctrl", "-lx"],
                            text=True,
                            stderr=subprocess.DEVNULL,
                        )
                        for line in output.splitlines():
                            if "skyscanner" in line.lower():
                                win_id = line.split()[0]
                                result = subprocess.run(
                                    ["wmctrl", "-ia", win_id],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                                if result.returncode == 0:
                                    if which("xdotool") is not None:
                                        subprocess.run(
                                            ["xdotool", "windowraise", win_id],
                                            stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL,
                                        )
                                    return True
                    except Exception:
                        pass
                if which("xdotool") is not None:
                    for name in ("Skyscanner", "skyscanner"):
                        result = subprocess.run(
                            ["xdotool", "search", "--onlyvisible", "--name", name, "windowactivate", "--sync"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                        if result.returncode == 0:
                            return True

            if which("xdotool") is not None:
                for cls in class_candidates:
                    result = subprocess.run(
                        ["xdotool", "search", "--onlyvisible", "--class", cls, "windowactivate", "--sync"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if result.returncode == 0:
                        return True
                for name in name_candidates:
                    result = subprocess.run(
                        ["xdotool", "search", "--onlyvisible", "--name", name, "windowactivate", "--sync"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if result.returncode == 0:
                        return True
            if which("wmctrl") is not None:
                for name in name_candidates:
                    result = subprocess.run(
                        ["wmctrl", "-a", name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if result.returncode == 0:
                        return True
            return False

        focused = False
        deadline = time.time() + float(os.environ.get("LUCY_FOCUS_WAIT_S", "2.0"))
        while time.time() < deadline and not focused:
            focused = _try_focus_once()
            if not focused:
                time.sleep(0.2)

        title = self._get_active_window_title()
        if focused:
            logger.debug("Foco aplicado a ventana objetivo: {}", target)
        if target.lower() == "firefox" and "skyscanner" not in title.lower():
            if which("wmctrl") is not None:
                try:
                    output = subprocess.check_output(["wmctrl", "-lx"], text=True, stderr=subprocess.DEVNULL)
                    for line in output.splitlines():
                        if "skyscanner" in line.lower() and "firefox" in line.lower():
                            win_id = line.split()[0]
                            subprocess.run(
                                ["wmctrl", "-ia", win_id],
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL,
                            )
                            if which("xdotool") is not None:
                                subprocess.run(
                                    ["xdotool", "windowraise", win_id],
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.DEVNULL,
                                )
                            break
                except Exception:
                    pass
        if focused:
            time.sleep(0.5)

    @property
    def name(self) -> str:
        return "capture_screen"

    @property
    def description(self) -> str:
        return "Captura la pantalla actual y devuelve la ruta al archivo."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "overlay_grid": {
                    "type": "boolean",
                    "description": "Si es true, dibuja una grilla con etiquetas A1..H10.",
                    "default": True,
                },
                "grid": {
                    "type": "boolean",
                    "description": "Alias de overlay_grid para pedir grilla.",
                },
            },
            "required": [],
        }

    def execute(self, overlay_grid: bool = True, grid: Optional[bool] = None) -> str:
        if grid is not None:
            overlay_grid = bool(grid)
        try:
            self._focus_target_window()
            self._log_active_window()
            if which("wmctrl") is not None and os.environ.get("LUCY_MAXIMIZE_ON_CAPTURE", "1") != "0":
                try:
                    subprocess.run(
                        ["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    logger.debug("🖥️ Ventana maximizada antes de capturar.")
                    time.sleep(0.5)
                except Exception:
                    pass
            # Avoid top-bar calendar on GNOME; windowactivate should be enough when cropping active window.
            if os.getenv("LUCY_SKIP_FOCUS_CLICK", "0") != "1" and os.getenv("LUCY_CAPTURE_ACTIVE_WINDOW", "0") != "1":
                region = self._active_window_region()
                if region:
                    x, y, w, h = region
                    click_x = x + max(20, w // 2)
                    # Evita la barra superior global y el UI del navegador.
                    click_y = y + min(max(80, h // 6), max(80, h - 10))
                    pyautogui.click(click_x, click_y)
                else:
                    sw, sh = pyautogui.size()
                    pyautogui.click(sw // 2, sh // 2)
                time.sleep(0.5)
        except Exception as exc:
            logger.warning("No pude enfocar ventana antes de capturar: %s", exc)
        logger.info("Capturando escritorio (overlay_grid={})", overlay_grid)
        try:
            region = self._active_window_region()
            if region:
                logger.info("🎯 Capturando region activa: {}", region)
            path = self._eye.capture(overlay_grid=overlay_grid, region=region)
            return json.dumps({"path": path}, ensure_ascii=False)
        except Exception as exc:
            logger.error("Error en DesktopVisionSkill: %s", exc)
            return f"Error al capturar la pantalla: {exc}"


class DesktopActionSkill(BaseSkill):
    def __init__(self, hand: Optional[DesktopHand] = None):
        self._hand = hand or DesktopHand()
        self._last_typed = None
        self._last_typed_is_url = False
        self._last_typed_app = None

    def _find_window_id(self, keywords: set[str]) -> Optional[str]:
        if which("wmctrl") is None:
            return None
        try:
            output = subprocess.check_output(["wmctrl", "-lx"], text=True, stderr=subprocess.DEVNULL)
        except Exception:
            return None
        for line in output.splitlines():
            lower = line.lower()
            if any(k for k in keywords if k and k in lower):
                parts = line.split()
                if parts:
                    return parts[0]
        return None

    def _window_region_by_id(self, win_id: str) -> Optional[tuple[int, int, int, int]]:
        if which("xwininfo") is None or not win_id:
            return None
        try:
            info = subprocess.check_output(["xwininfo", "-id", str(win_id)], text=True, stderr=subprocess.DEVNULL)
        except Exception:
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

    def _maximize_active_window(self) -> None:
        if which("wmctrl") is None:
            return
        if os.environ.get("LUCY_MAXIMIZE_ON_FOCUS", "1") == "0":
            return
        try:
            subprocess.run(
                ["wmctrl", "-r", ":ACTIVE:", "-b", "add,maximized_vert,maximized_horz"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            logger.debug("🖥️ Ventana maximizada forzosamente.")
            time.sleep(0.5)
        except Exception:
            return

    def _ensure_focus(self, target_title_keyword: Optional[str] = None) -> bool:
        """Robar el foco agresivamente usando wmctrl y xdotool."""
        target = (
            target_title_keyword
            or os.environ.get("LUCY_FOCUS_APP")
            or _get_last_app()
        )
        if not target:
            if which("google-chrome") is not None:
                target = "google-chrome"
            elif which("chromium") is not None:
                target = "chromium"
            else:
                target = "firefox"

        target = str(target or "").strip()
        if not target:
            return True
        logger.debug(f"🛡️ Focus Guard 2.0: Buscando '{target}'...")

        titles = {target}
        classes = {target}
        lower_target = target.lower()
        if "chrome" in lower_target or "chromium" in lower_target:
            titles.update({"Google Chrome", "Chrome", "Chromium"})
            classes.update({"google-chrome", "Google-chrome", "chromium", "Chromium"})
        if "firefox" in lower_target or "mozilla" in lower_target:
            titles.update({"Firefox", "Mozilla Firefox"})
            classes.update({"firefox", "Navigator", "navigator"})

        # Estrategia 1: wmctrl (Suele ser el más efectivo en GNOME/X11)
        if which("wmctrl") is not None:
            for title in titles:
                if not title:
                    continue
                subprocess.run(
                    ["wmctrl", "-R", title],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            for cls in classes:
                if not cls:
                    continue
                subprocess.run(
                    ["wmctrl", "-x", "-R", cls],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            time.sleep(0.3)

        # Verificación temprana
        active_title = self._get_active_window_title()
        active_lower = active_title.lower()
        verify_keywords = {lower_target}
        if "chrome" in lower_target or "chromium" in lower_target:
            verify_keywords.update({"chrome", "chromium", "google chrome"})
        if "firefox" in lower_target or "mozilla" in lower_target:
            verify_keywords.update({"firefox", "mozilla", "navigator"})
        if any(k for k in verify_keywords if k and k in active_lower):
            logger.debug(f"✅ Foco confirmado (via wmctrl). Activa: {active_title}")
            self._maximize_active_window()
            return True

        # Estrategia 2: xdotool search --class (Más robusto que --name)
        if which("xdotool") is not None:
            for cls in classes:
                if not cls:
                    continue
                subprocess.run(
                    ["xdotool", "search", "--onlyvisible", "--class", cls, "windowactivate", "--sync"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            for title in titles:
                if not title:
                    continue
                subprocess.run(
                    ["xdotool", "search", "--onlyvisible", "--name", title, "windowactivate", "--sync"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            time.sleep(0.3)

        # Verificación final
        active_title = self._get_active_window_title()
        active_lower = active_title.lower()
        if any(k for k in verify_keywords if k and k in active_lower):
            logger.debug(f"✅ Foco confirmado. Activa: {active_title}")
            self._maximize_active_window()
            return True

        # Estrategia 3: activar por window id + fallback click
        win_id = self._find_window_id(verify_keywords)
        if win_id:
            if which("wmctrl") is not None:
                subprocess.run(
                    ["wmctrl", "-ia", win_id],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            if which("xdotool") is not None:
                subprocess.run(
                    ["xdotool", "windowactivate", "--sync", win_id],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["xdotool", "windowraise", win_id],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            time.sleep(0.3)
            active_title = self._get_active_window_title()
            active_lower = active_title.lower()
            if any(k for k in verify_keywords if k and k in active_lower):
                logger.debug(f"✅ Foco confirmado (via window id). Activa: {active_title}")
                self._maximize_active_window()
                return True

            if os.environ.get("LUCY_FOCUS_CLICK", "1") != "0":
                region = self._window_region_by_id(win_id)
                if region:
                    x, y, w, h = region
                    click_x = x + max(20, w // 2)
                    click_y = y + min(max(80, h // 6), max(80, h - 10))
                    pyautogui.click(click_x, click_y)
                    time.sleep(0.2)
                    active_title = self._get_active_window_title()
                    active_lower = active_title.lower()
                    if any(k for k in verify_keywords if k and k in active_lower):
                        logger.debug(f"✅ Foco confirmado (via click). Activa: {active_title}")
                        self._maximize_active_window()
                        return True

        logger.warning(
            f"⚠️ Falló el cambio de foco. Ventana activa sigue siendo: '{active_title}'"
        )
        return False

    def _get_active_window_title(self) -> str:
        """Helper para obtener título seguro."""
        try:
            if which("xdotool") is not None:
                return subprocess.check_output(
                    ["xdotool", "getactivewindow", "getwindowname"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            return ""
        except Exception:
            return ""

    def _active_window_region(self) -> Optional[tuple[int, int, int, int]]:
        if which("xwininfo") is None:
            return None
        win_id = None
        if which("xdotool") is not None:
            for cmd in (["xdotool", "getactivewindow"], ["xdotool", "getwindowfocus"]):
                try:
                    win_id = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                    if win_id:
                        break
                except Exception:
                    continue
        if not win_id and which("wmctrl") is not None:
            try:
                output = subprocess.check_output(["wmctrl", "-lx"], text=True, stderr=subprocess.DEVNULL)
                for line in output.splitlines():
                    lower = line.lower()
                    if (
                        "skyscanner" in lower
                        or "firefox" in lower
                        or "chrome" in lower
                        or "chromium" in lower
                    ):
                        win_id = line.split()[0]
                        break
            except Exception:
                win_id = None
        if not win_id:
            return None
        try:
            info = subprocess.check_output(["xwininfo", "-id", win_id], text=True, stderr=subprocess.DEVNULL)
        except Exception:
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

    def _calculate_absolute_coords(self, grid_str: str) -> tuple[int, int]:
        """Traduce 'C4' a coordenadas de pantalla (X, Y) considerando el recorte de ventana."""
        code = str(grid_str or "").strip().upper()
        if not code or not any(ch.isdigit() for ch in code):
            raise ValueError(f"Grid code invalido: {grid_str}")

        match = re.match(r"^([A-Z])(\d{1,2})$", code)
        if match:
            col_letter, row_str = match.groups()
            col_index = ord(col_letter) - ord("A")
            row_index = int(row_str) - 1
        else:
            nums = re.findall(r"\d{1,2}", code)
            if len(nums) != 2:
                raise ValueError(f"Grid code invalido: {grid_str}")
            a = int(nums[0])
            b = int(nums[1])
            candidates = []
            if 1 <= a <= GridMapper.COLS and 1 <= b <= GridMapper.ROWS:
                candidates.append((a - 1, b - 1))
            if 1 <= a <= GridMapper.ROWS and 1 <= b <= GridMapper.COLS:
                candidates.append((b - 1, a - 1))
            if not candidates:
                raise ValueError(f"Grid code invalido: {grid_str}")
            col_index, row_index = candidates[0]

        if col_index < 0 or col_index >= GridMapper.COLS:
            raise ValueError(f"Columna fuera de rango: {col_index + 1}")
        if row_index < 0 or row_index >= GridMapper.ROWS:
            raise ValueError(f"Fila fuera de rango: {row_index + 1}")

        region = self._active_window_region()
        if region:
            win_x, win_y, win_w, win_h = region
        else:
            screen = pyautogui.size()
            win_x, win_y, win_w, win_h = 0, 0, screen.width, screen.height

        rel_x = (col_index + 0.5) / GridMapper.COLS
        rel_y = (row_index + 0.5) / GridMapper.ROWS
        abs_x = win_x + int(rel_x * win_w)
        abs_y = win_y + int(rel_y * win_h)
        return abs_x, abs_y

    def _extract_domain(self, text: str) -> Optional[str]:
        if not text:
            return None
        lowered = text.lower().strip()
        match = re.search(r"[a-z][a-z0-9-]*(?:\\.[a-z0-9-]+)+", lowered)
        if not match:
            return None
        domain = match.group(0)
        domain = domain.lstrip("0123456789").lstrip(".")
        return domain or None

    def _sanitize_typed_text(self, text: str) -> str:
        raw = str(text).strip()
        lowered = raw.lower()
        candidate = raw
        if "7" in raw and ("http" in lowered or "www" in lowered or "://" in lowered):
            candidate = raw.replace("7", "/")

        domain = None
        if "://" in candidate:
            parsed = urlparse(candidate)
            if parsed.netloc:
                domain = parsed.netloc
        if not domain:
            domain = self._extract_domain(candidate)
        if domain:
            if domain.startswith("www."):
                domain = domain[4:]
            return domain
        return raw

    def _verify_process(self, name: str) -> Optional[bool]:
        if which("pgrep") is None:
            return None
        try:
            result = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True)
            if result.returncode == 0:
                return True
            # fallback: match by substring
            result = subprocess.run(["pgrep", "-f", name], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return None

    def _ensure_firefox(self) -> None:
        preferred = os.environ.get("LUCY_BROWSER_BIN")
        browser = None
        if preferred and which(preferred) is not None:
            browser = preferred
        elif which("firefox") is not None:
            browser = "firefox"
        elif which("google-chrome") is not None:
            browser = "google-chrome"
        elif which("chromium") is not None:
            browser = "chromium"

        if not browser:
            return

        running = self._verify_process(browser)
        if running is False and which(browser) is not None:
            try:
                subprocess.Popen([browser], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1.5)
            except Exception:
                pass
        if which("wmctrl") is not None:
            try:
                title = "Firefox"
                if browser == "google-chrome":
                    title = "Google Chrome"
                elif browser == "chromium":
                    title = "Chromium"
                subprocess.run(["wmctrl", "-a", title], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        _set_last_app(browser)

    @property
    def name(self) -> str:
        return "perform_action"

    @property
    def description(self) -> str:
        return "Controla mouse y teclado: mover/click, escribir, scroll y hotkeys."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "Acción a ejecutar.",
                    "enum": ["move_and_click", "click", "click_grid", "type", "scroll", "hotkey"],
                },
                "x": {"type": "integer", "description": "Coordenada X."},
                "y": {"type": "integer", "description": "Coordenada Y."},
                "grid": {
                    "type": "string",
                    "description": "Coordenada de grilla (ej: C4).",
                },
                "grid_id": {
                    "type": "string",
                    "description": "Alias de grid para click en grilla (ej: C4).",
                },
                "grid_code": {
                    "type": "string",
                    "description": "Alias de grid para click en grilla (ej: C4).",
                },
                "text": {"type": "string", "description": "Texto a escribir."},
                "clicks": {"type": "integer", "description": "Clicks de scroll (positivo/negativo)."},
                "keys": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Lista de teclas para hotkey (ej: ['ctrl', 'c']).",
                },
                "button": {
                    "type": "string",
                    "description": "Botón del mouse (left/right/middle).",
                    "default": "left",
                },
                "duration": {
                    "type": "number",
                    "description": "Duración del movimiento del mouse en segundos.",
                    "default": 0.3,
                },
            },
            "required": ["action"],
        }

    def execute(self, **kwargs) -> str:
        action = kwargs.get("action") or kwargs.get("action_type") or kwargs.get("command")
        if action in {"click", "click_grid"}:
            action = "move_and_click"
        grid = (
            kwargs.get("grid")
            or kwargs.get("grid_id")
            or kwargs.get("grid_code")
            or kwargs.get("coordinate")
            or kwargs.get("location")
        )
        x = kwargs.get("x")
        y = kwargs.get("y")
        text = kwargs.get("text")
        clicks = kwargs.get("clicks")
        keys = kwargs.get("keys")
        button = kwargs.get("button", "left")
        duration = kwargs.get("duration", 0.3)
        # Ignora parametros basura (ej: seconds)
        _ = kwargs.get("seconds")

        logger.info(f"Acción de escritorio: {action}")
        try:
            if not action:
                return "Error: se requiere action para ejecutar la accion."

            if action == "move_and_click":
                if not self._ensure_focus():
                    return "Error: foco no confirmado antes del click."
                if grid:
                    if isinstance(grid, (list, tuple)) and len(grid) >= 2:
                        self._hand.move_and_click(grid[0], grid[1], duration=duration, button=button)
                        if text is not None:
                            cleaned = self._sanitize_typed_text(str(text))
                            if self._extract_domain(cleaned):
                                self._ensure_firefox()
                            self._hand.type(cleaned)
                            if keys:
                                raw_keys = keys
                                if isinstance(raw_keys, str):
                                    raw_keys = [k for k in raw_keys.replace("+", " ").split() if k]
                                for k in raw_keys:
                                    k = str(k).lower().strip()
                                    if k in {"enter", "return"}:
                                        self._hand.hotkey("enter")
                                    elif k == "tab":
                                        self._hand.hotkey("tab")
                                    time.sleep(0.05)
                        return "OK: click ejecutado."
                    x_abs, y_abs = self._calculate_absolute_coords(str(grid))
                    logger.info(f"🖱️ Click Grid {grid} -> Screen ({x_abs}, {y_abs})")
                    self._hand.move_and_click(x_abs, y_abs, duration=duration, button=button)
                    if text is not None:
                        cleaned = self._sanitize_typed_text(str(text))
                        if self._extract_domain(cleaned):
                            self._ensure_firefox()
                        self._hand.type(cleaned)
                        if keys:
                            raw_keys = keys
                            if isinstance(raw_keys, str):
                                raw_keys = [k for k in raw_keys.replace("+", " ").split() if k]
                            for k in raw_keys:
                                k = str(k).lower().strip()
                                if k in {"enter", "return"}:
                                    self._hand.hotkey("enter")
                                elif k == "tab":
                                    self._hand.hotkey("tab")
                                time.sleep(0.05)
                    return f"OK: click ejecutado en grilla {grid}."
                if x is None or y is None:
                    return "Error: se requieren x e y o grid para move_and_click."
                self._hand.move_and_click(x, y, duration=duration, button=button)
                if text is not None:
                    cleaned = self._sanitize_typed_text(str(text))
                    if self._extract_domain(cleaned):
                        self._ensure_firefox()
                    self._hand.type(cleaned)
                    if keys:
                        raw_keys = keys
                        if isinstance(raw_keys, str):
                            raw_keys = [k for k in raw_keys.replace("+", " ").split() if k]
                        for k in raw_keys:
                            k = str(k).lower().strip()
                            if k in {"enter", "return"}:
                                self._hand.hotkey("enter")
                            elif k == "tab":
                                self._hand.hotkey("tab")
                            time.sleep(0.05)
                return "OK: click ejecutado."

            if action == "type":
                if text is None:
                    return "Error: se requiere texto para type."
                if not self._ensure_focus():
                    return "Error: foco no confirmado antes de escribir."
                if keys:
                    raw_keys = keys
                    if isinstance(raw_keys, str):
                        raw_keys = [k for k in raw_keys.replace("+", " ").split() if k]
                    clean_keys = []
                    for k in raw_keys:
                        k = str(k).lower().strip()
                        if k in {"control", "ctrl"}:
                            clean_keys.append("ctrl")
                        elif k in {"alt"}:
                            clean_keys.append("alt")
                        elif k in {"shift"}:
                            clean_keys.append("shift")
                        else:
                            clean_keys.append(k)
                    pre_keys: list[str] = []
                    post_keys: list[str] = []
                    for k in clean_keys:
                        if k in {"enter", "return"}:
                            post_keys.append("enter")
                        elif k == "tab":
                            post_keys.append("tab")
                        else:
                            pre_keys.append(k)
                    if pre_keys:
                        logger.info(f"⌨️ Pre-hotkey para type: {pre_keys}")
                        if "ctrl" in pre_keys and ("l" in pre_keys or "f6" in pre_keys):
                            self._ensure_firefox()
                        if any(k in {"ctrl", "alt", "shift"} for k in pre_keys):
                            self._hand.hotkey(*pre_keys)
                        else:
                            for key in pre_keys:
                                self._hand.hotkey(key)
                                time.sleep(0.05)
                        time.sleep(0.1)
                cleaned = self._sanitize_typed_text(str(text))
                if cleaned != text:
                    logger.info(f"Texto normalizado para tipeo: '{text}' -> '{cleaned}'")
                if self._extract_domain(cleaned):
                    self._ensure_firefox()
                self._hand.type(cleaned)
                if keys:
                    raw_keys = keys
                    if isinstance(raw_keys, str):
                        raw_keys = [k for k in raw_keys.replace("+", " ").split() if k]
                    clean_keys = []
                    for k in raw_keys:
                        k = str(k).lower().strip()
                        if k in {"control", "ctrl"}:
                            clean_keys.append("ctrl")
                        elif k in {"alt"}:
                            clean_keys.append("alt")
                        elif k in {"shift"}:
                            clean_keys.append("shift")
                        else:
                            clean_keys.append(k)
                    post_keys: list[str] = []
                    for k in clean_keys:
                        if k in {"enter", "return"}:
                            post_keys.append("enter")
                        elif k == "tab":
                            post_keys.append("tab")
                    if post_keys:
                        logger.info(f"⌨️ Post-hotkey para type: {post_keys}")
                        for key in post_keys:
                            self._hand.hotkey(key)
                            time.sleep(0.05)
                self._last_typed = cleaned
                self._last_typed_is_url = self._extract_domain(cleaned) is not None
                if cleaned.lower() in {"firefox"}:
                    self._last_typed_app = "firefox"
                return "OK: texto escrito."

            if action == "scroll":
                if clicks is None:
                    return "Error: se requiere clicks para scroll."
                if not self._ensure_focus():
                    return "Error: foco no confirmado antes del scroll."
                self._hand.scroll(clicks)
                return "OK: scroll ejecutado."

            if action == "hotkey":
                raw_keys = keys if keys is not None else text
                if isinstance(raw_keys, str):
                    raw_keys = [k for k in raw_keys.replace("+", " ").split() if k]
                if not raw_keys and text:
                    raw_keys = [k for k in str(text).replace("+", " ").split() if k]
                if not raw_keys:
                    return "Error: se requiere lista de teclas para hotkey."

                if not self._ensure_focus():
                    return "Error: foco no confirmado antes del hotkey."

                clean_keys = []
                requires_focus = False
                for k in raw_keys:
                    k = str(k).lower().strip()
                    if k in {"pagedown", "avpag", "^[[6~"}:
                        clean_keys.append("pagedown")
                        requires_focus = True
                    elif k in {"pageup", "repag", "^[[5~"}:
                        clean_keys.append("pageup")
                        requires_focus = True
                    elif k in {"down", "arrowdown", "abajo"}:
                        clean_keys.append("down")
                        requires_focus = True
                    elif k in {"up", "arrowup", "arriba"}:
                        clean_keys.append("up")
                        requires_focus = True
                    elif k in {"enter", "return", "entrar"}:
                        clean_keys.append("enter")
                    elif k in {"espacio", "space"}:
                        clean_keys.append("space")
                        requires_focus = True
                    else:
                        clean_keys.append(k)

                logger.info(f"⌨️ Teclas normalizadas: {clean_keys}")

                if requires_focus:
                    try:
                        sw, sh = pyautogui.size()
                        pyautogui.click(sw // 2, sh // 2)
                        time.sleep(0.2)
                    except Exception as exc:
                        logger.warning("No se pudo asegurar el foco antes del hotkey: %s", exc)

                keys_lower = [k.lower() for k in clean_keys]
                if "ctrl" in keys_lower and ("l" in keys_lower or "f6" in keys_lower):
                    self._ensure_firefox()
                self._hand.hotkey(*clean_keys)
                if "enter" in keys_lower and (self._last_typed_is_url or self._last_typed_app == "firefox"):
                    browser = os.environ.get("LUCY_BROWSER_BIN") or _get_last_app() or "firefox"
                    running = self._verify_process(browser)
                    if running is True:
                        return f"OK: hotkey ejecutado. Verificación: {browser} está corriendo."
                    if running is False:
                        return f"ERROR: {browser} NO está corriendo. La acción falló."
                return "OK: hotkey ejecutado."

            return "Acción no reconocida."
        except Exception as exc:
            logger.error(f"❌ Error CRITICO en DesktopActionSkill: {exc}")
            return f"Error ejecutando accion: {exc}"


class DesktopLaunchSkill(BaseSkill):
    def __init__(self):
        self._default_app = "firefox"

    def _verify_process(self, name: str) -> Optional[bool]:
        if which("pgrep") is None:
            return None
        try:
            result = subprocess.run(["pgrep", "-x", name], capture_output=True, text=True)
            if result.returncode == 0:
                return True
            result = subprocess.run(["pgrep", "-f", name], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return None

    @property
    def name(self) -> str:
        return "launch_app"

    @property
    def description(self) -> str:
        return "Lanza una aplicación directamente (mejor que usar teclado)."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Nombre del binario (ej: firefox, code).",
                },
                "url": {
                    "type": "string",
                    "description": "URL o archivo a abrir con la app.",
                },
                "wait_s": {
                    "type": "number",
                    "description": "Segundos de espera tras lanzar la app (por defecto 3).",
                    "default": 3,
                },
            },
            "required": [],
        }

    def execute(self, app_name: Optional[str] = None, url: Optional[str] = None, **kwargs) -> str:
        name = (app_name or "").strip() or self._default_app
        _set_last_app(name)
        wait_s = kwargs.get("wait_s", 3)
        if which(name) is None:
            return f"Error: app no encontrada ({name})."

        command = [name]
        if url:
            command.append(str(url))

        try:
            logger.info(
                "Lanzando app {} (DISPLAY={}, XAUTHORITY={})",
                name,
                os.environ.get("DISPLAY"),
                os.environ.get("XAUTHORITY"),
            )
            running = self._verify_process(name)
            if running is True:
                # App ya abierta: enviar URL y enfocar sin abrir nuevas ventanas
                if url:
                    try:
                        if name.lower() == "firefox":
                            subprocess.Popen([name, "--new-tab", str(url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        elif which("xdg-open") is not None:
                            subprocess.Popen(["xdg-open", str(url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        else:
                            subprocess.Popen([name, "--new-tab", str(url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                if name.lower() == "firefox" and which("wmctrl") is not None:
                    try:
                        subprocess.run(
                            ["wmctrl", "-a", "Firefox"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
                    except Exception:
                        pass
                return f"OK: app ya estaba abierta ({name})."
            subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            try:
                time.sleep(float(wait_s))
            except Exception:
                time.sleep(3)
            if name.lower() == "firefox" and which("wmctrl") is not None:
                try:
                    subprocess.run(
                        ["wmctrl", "-a", "Firefox"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                except Exception:
                    pass
            running = self._verify_process(name)
            if running is False and url and which("xdg-open") is not None:
                try:
                    if name.lower() == "firefox":
                        subprocess.Popen([name, "--new-tab", str(url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    else:
                        subprocess.Popen(["xdg-open", str(url)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.5)
                    running = self._verify_process(name)
                except Exception:
                    pass
            if running is False:
                return f"Error: app no se abrio ({name})."
            return f"OK: app lanzada ({name})."
        except Exception as exc:
            return f"Error lanzando app ({name}): {exc}"


class DesktopZoomSkill(BaseSkill):
    def __init__(self):
        self._default_path = "/tmp/lucy_zoom.jpg"

    @property
    def name(self) -> str:
        return "capture_region"

    @property
    def description(self) -> str:
        return "Captura un recorte de una celda de la grilla para lectura precisa."

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "cell_label": {
                    "type": "string",
                    "description": "Alias de grid (ej: C4).",
                },
                "grid": {
                    "type": "string",
                    "description": "Coordenada de grilla (ej: C4).",
                },
                "grid_id": {
                    "type": "string",
                    "description": "Alias de grid para recorte (ej: C4).",
                },
                "grid_code": {
                    "type": "string",
                    "description": "Alias de grid para recorte (ej: C4).",
                },
                "padding": {
                    "type": "integer",
                    "description": "Padding en pixeles alrededor de la celda.",
                    "default": 60,
                },
                "out_path": {
                    "type": "string",
                    "description": "Ruta de salida para guardar el recorte.",
                },
            },
            "required": [],
        }

    def execute(self, **kwargs) -> str:
        grid = (
            kwargs.get("cell_label")
            or kwargs.get("grid")
            or kwargs.get("grid_id")
            or kwargs.get("grid_code")
            or kwargs.get("coordinate")
            or kwargs.get("location")
        )
        padding = int(kwargs.get("padding", 60) or 60)
        out_path = kwargs.get("out_path") or self._default_path
        if not grid:
            return "Error: se requiere grid para capture_region."

        try:
            left, top, width, height = GridMapper.get_cell_bounds(str(grid))
            left = max(left - padding, 0)
            top = max(top - padding, 0)
            width = width + padding * 2
            height = height + padding * 2
            zoom_img = pyautogui.screenshot(region=(left, top, width, height))
            zoom_img.save(out_path)
            return json.dumps({"path": out_path}, ensure_ascii=False)
        except Exception as exc:
            return f"Error en capture_region: {exc}"


class DesktopSkillWrapper:
    def __init__(self):
        self.vision_skill = DesktopVisionSkill()
        self.action_skill = DesktopActionSkill()
        self.launch_skill = DesktopLaunchSkill()
        self.zoom_skill = DesktopZoomSkill()

    def tools(self) -> List[BaseSkill]:
        return [self.vision_skill, self.action_skill, self.launch_skill, self.zoom_skill]

    def capture_screen(self, overlay_grid: bool = True) -> str:
        return self.vision_skill.execute(overlay_grid=overlay_grid)

    def perform_action(self, **kwargs: Any) -> str:
        return self.action_skill.execute(**kwargs)
