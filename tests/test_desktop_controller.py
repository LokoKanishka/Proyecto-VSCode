import pyautogui

from src.vision.desktop_controller import DesktopController


def test_compute_grid_coordinates(monkeypatch):
    """La celda A1 debe mapear al centro superior izquierdo."""
    monkeypatch.setattr(pyautogui, "size", lambda: (800, 600))
    controller = DesktopController()
    assert controller.compute_grid_coordinates("A1") == (50, 30)


def test_compute_grid_bounds(monkeypatch):
    """El ancho y alto de cada celda deben corresponder al grid."""
    monkeypatch.setattr(pyautogui, "size", lambda: (800, 600))
    controller = DesktopController()
    left, top, width, height = controller.compute_grid_bounds("H10")
    assert width == 100
    assert height == 60
    assert left == 700
    assert top == 540
