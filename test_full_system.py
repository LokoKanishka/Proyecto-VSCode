import importlib
import os
import shutil
from pathlib import Path


def _check_import(module_name: str) -> bool:
    try:
        importlib.import_module(module_name)
        return True
    except Exception:
        return False


def test_full_system() -> None:
    print("\nDIAGNOSTICO DE SISTEMAS VITALES")

    # 1) Motor
    try:
        from src.engine.ollama_engine import OllamaEngine
        print("OK: Importacion de OllamaEngine")
    except Exception as exc:
        print(f"ERROR: No se pudo importar OllamaEngine: {exc}")
        return

    # 2) Inicializacion del motor (sin hablar)
    try:
        engine = OllamaEngine(model=os.getenv("LUCY_OLLAMA_MODEL", "llama3.1:8b"))
        print("OK: Motor inicializado")
    except Exception as exc:
        print(f"ERROR: Fallo al iniciar motor: {exc}")
        return

    # 3) Skills de escritorio
    if hasattr(engine, "desktop_skills"):
        print("OK: Skills de escritorio detectadas")
    else:
        print("ALERTA: Skills de escritorio no encontradas")

    # 4) Voz: rutas reales del repo (no hay src/senses en este monolito)
    voice_bridge_available = _check_import("src.engine.voice_bridge")
    print(f"Voz (voice_bridge import): {'OK' if voice_bridge_available else 'NO'}")

    mimic3_path = shutil.which("mimic3")
    print(f"mimic3 CLI: {'OK' if mimic3_path else 'NO'}")

    modular_node = Path("external/nodo-de-voz-modular-de-lucy/app.py")
    print(f"Nodo modular (app.py): {'OK' if modular_node.exists() else 'NO'}")

    # 5) Oido (faster-whisper)
    whisper_ok = _check_import("faster_whisper")
    print(f"Oido (faster_whisper import): {'OK' if whisper_ok else 'NO'}")


if __name__ == "__main__":
    test_full_system()
