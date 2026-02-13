"""
LUCY HOST AGENT - Puente de Ejecución X11/System (File-IPC).
Se ejecuta en el host, fuera del sandbox de Ray/Docker si es necesario.
Ubicación: scripts/x11_file_agent.py
"""
import time
import os
import json
import glob
import pyautogui
import subprocess
from pathlib import Path

# Configuración
PROJECT_ROOT = Path(__file__).parent.parent
IPC_ROOT = PROJECT_ROOT / "data/ipc"
INBOX_DIR = IPC_ROOT / "inbox"
OUTBOX_DIR = IPC_ROOT / "outbox"

print(f"👻 LUCY HOST AGENT escuchando en: {INBOX_DIR}")

def process_command(cmd_file):
    try:
        with open(cmd_file, "r") as f:
            data = json.load(f)
            
        cmd_id = data.get("id")
        action = data.get("type")
        params = data.get("params", {})
        
        print(f"⚡ Ejecutando: {action} [{cmd_id}]")
        
        result = {"id": cmd_id, "status": "success", "data": None}
        
        # --- Dispatch de Acciones ---
        if action == "terminal_cmd":
            # Ejecutar comando de terminal
            try:
                out = subprocess.check_output(params.get("command"), shell=True, stderr=subprocess.STDOUT)
                result["data"] = out.decode("utf-8")
            except subprocess.CalledProcessError as e:
                result["status"] = "error"
                result["data"] = e.output.decode("utf-8")
                
        elif action == "mouse_move":
            x, y = params.get("x"), params.get("y")
            pyautogui.moveTo(x, y)
            
        elif action == "mouse_click":
            x, y = params.get("x"), params.get("y")
            if x and y:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
                
        elif action == "type_text":
            text = params.get("text")
            pyautogui.write(text, interval=0.01)

        elif action == "press_key":
            keys = params.get("keys", [])
            if isinstance(keys, str): keys = [keys]
            pyautogui.hotkey(*keys)
            
        else:
            result["status"] = "error"
            result["data"] = f"Unknown action: {action}"

        # --- Escribir Resultado ---
        out_path = OUTBOX_DIR / f"{cmd_id}.result.json"
        tmp_path = out_path.with_suffix(".tmp")
        
        with open(tmp_path, "w") as f:
            json.dump(result, f)
        os.rename(tmp_path, out_path)
        
    except Exception as e:
        print(f"❌ Error procesando {cmd_file}: {e}")
    finally:
        # Eliminar comando procesado
        try:
            os.remove(cmd_file)
        except:
            pass

def main_loop():
    # Asegurar directorios
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    
    while True:
        # Polling simple (inotify es mejor pero requiere dependencias extra)
        files = list(INBOX_DIR.glob("*.json"))
        if files:
            for f in files:
                process_command(f)
        
        time.sleep(0.1)

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\n🛑 Host Agent detenido.")
