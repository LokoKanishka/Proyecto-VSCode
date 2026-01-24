import json
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


class DesktopVisionSkill(BaseSkill):
    def __init__(self, eye: Optional[DesktopEye] = None):
        self._eye = eye or DesktopEye()

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
        logger.info("Capturando escritorio (overlay_grid=%s)", overlay_grid)
        try:
            path = self._eye.capture(overlay_grid=overlay_grid)
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
        running = self._verify_process("firefox")
        if running is False and which("firefox") is not None:
            try:
                subprocess.Popen(["firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(1.5)
            except Exception:
                pass
        if which("wmctrl") is not None:
            try:
                subprocess.run(["wmctrl", "-a", "Firefox"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

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
                if grid:
                    if isinstance(grid, (list, tuple)) and len(grid) >= 2:
                        self._hand.move_and_click(grid[0], grid[1], duration=duration, button=button)
                        return "OK: click ejecutado."
                    self._hand.move_and_click(str(grid), duration=duration, button=button)
                    return f"OK: click ejecutado en grilla {grid}."
                if x is None or y is None:
                    return "Error: se requieren x e y o grid para move_and_click."
                self._hand.move_and_click(x, y, duration=duration, button=button)
                return "OK: click ejecutado."

            if action == "type":
                if text is None:
                    return "Error: se requiere texto para type."
                cleaned = self._sanitize_typed_text(str(text))
                if cleaned != text:
                    logger.info(f"Texto normalizado para tipeo: '{text}' -> '{cleaned}'")
                if self._extract_domain(cleaned):
                    self._ensure_firefox()
                self._hand.type(cleaned)
                self._last_typed = cleaned
                self._last_typed_is_url = self._extract_domain(cleaned) is not None
                if cleaned.lower() in {"firefox"}:
                    self._last_typed_app = "firefox"
                return "OK: texto escrito."

            if action == "scroll":
                if clicks is None:
                    return "Error: se requiere clicks para scroll."
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

                clean_keys = []
                requires_focus = False
                for k in raw_keys:
                    k = str(k).lower().strip()
                    if k in {"baja", "scroll", "down", "pagedown", "avpag", "^[[6~"}:
                        clean_keys.append("pagedown")
                        requires_focus = True
                    elif k in {"sube", "up", "pageup", "repag", "^[[5~"}:
                        clean_keys.append("pageup")
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
                    running = self._verify_process("firefox")
                    if running is True:
                        return "OK: hotkey ejecutado. Verificación: Firefox está corriendo."
                    if running is False:
                        return "ERROR: Firefox NO está corriendo. La acción falló."
                return "OK: hotkey ejecutado."

            return "Acción no reconocida."
        except Exception as exc:
            logger.error(f"❌ Error CRITICO en DesktopActionSkill: {exc}")
            return f"Error ejecutando accion: {exc}"


class DesktopSkillWrapper:
    def __init__(self):
        self.vision_skill = DesktopVisionSkill()
        self.action_skill = DesktopActionSkill()

    def tools(self) -> List[BaseSkill]:
        return [self.vision_skill, self.action_skill]

    def capture_screen(self, overlay_grid: bool = True) -> str:
        return self.vision_skill.execute(overlay_grid=overlay_grid)

    def perform_action(self, **kwargs: Any) -> str:
        return self.action_skill.execute(**kwargs)
