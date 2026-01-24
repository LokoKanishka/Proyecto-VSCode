from typing import Iterable, Optional, Union

import pyautogui

from src.skills.grid_mapper import GridMapper


class DesktopHand:
    def __init__(self, pause: float = 0.5, failsafe: bool = True):
        pyautogui.FAILSAFE = bool(failsafe)
        pyautogui.PAUSE = float(pause)

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

        pyautogui.moveTo(target_x, target_y, duration=duration)
        pyautogui.click(button=button)

    def type(self, text: str) -> None:
        pyautogui.typewrite(str(text), interval=0.02)

    def scroll(self, clicks: int) -> None:
        pyautogui.scroll(int(clicks))

    def hotkey(self, *args: Iterable[str]) -> None:
        pyautogui.hotkey(*args)
