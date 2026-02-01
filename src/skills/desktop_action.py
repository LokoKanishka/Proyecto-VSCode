from typing import Iterable, Optional, Union

import pyautogui

from src.skills.grid_mapper import GridMapper


class DesktopHand:
    def __init__(self, pause: float = 0.5, failsafe: bool = True):
        pyautogui.FAILSAFE = bool(failsafe)
        pyautogui.PAUSE = float(pause)
        self.is_wayland = os.environ.get("XDG_SESSION_TYPE") == "wayland" or os.environ.get("WAYLAND_DISPLAY")
        if self.is_wayland:
            from src.control.wayland_input import WaylandInput
            self.wayland_input = WaylandInput()
        else:
            self.wayland_input = None

    def move_and_click(
        self,
        x: Union[int, str],
        y: Optional[int] = None,
        duration: float = 0.3,
        button: str = "left",
    ) -> None:
        if isinstance(x, str):
            target_x, target_y = GridMapper.get_coordinates(x)
        else:
            if y is None:
                raise ValueError("Se requiere y cuando x es numerico")
            target_x, target_y = int(x), int(y)

        if self.is_wayland and self.wayland_input:
            self.wayland_input.move_to(target_x, target_y)
            time.sleep(0.1)
            self.wayland_input.click(button=button)
        else:
            pyautogui.moveTo(target_x, target_y, duration=duration)
            pyautogui.click(button=button)

    def type(self, text: str) -> None:
        if self.is_wayland and self.wayland_input:
            self.wayland_input.type_text(str(text))
        else:
            pyautogui.typewrite(str(text), interval=0.02)

    def scroll(self, clicks: int) -> None:
        if self.is_wayland:
            # ydotool scroll is a bit different, but for now we skip or use fallback
            pyautogui.scroll(int(clicks))
        else:
            pyautogui.scroll(int(clicks))

    def hotkey(self, *args: Iterable[str]) -> None:
        if self.is_wayland and self.wayland_input:
            # Simplified hotkey for ydotool
            combo = "+".join(args)
            self.wayland_input.key_press(combo)
        else:
            pyautogui.hotkey(*args)
