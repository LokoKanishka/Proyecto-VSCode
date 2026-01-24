from src.skills.desktop_vision import DesktopEye


def test():
    print("Probando ojos de Lucy...")
    eye = DesktopEye()
    path = eye.capture(overlay_grid=True)
    print(f"Captura guardada en: {path}")
    print("Abri la imagen y verifica la grilla roja/cian.")


if __name__ == "__main__":
    test()
