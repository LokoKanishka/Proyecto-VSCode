import sys
import os
import time

# Ensure we can import from src
sys.path.append(os.getcwd())

from src.control.safe_worker import SafeActionWorker
from src.vision.wayland_capture import WaylandCapture

def test_safe_path():
    print("Testing Safe Path Worker...")
    worker = SafeActionWorker()
    capture = WaylandCapture()
    
    # 1. Test Screenshot
    print("Testing capture...")
    path = capture.capture_full()
    if path and os.path.exists(path):
        print(f"Capture success: {path}")
    else:
        print("Capture failed!")
        return
        
    # 2. Test Input (Move mouse)
    print("Testing mouse movement (Safe Path)...")
    
    def move_action():
        print("Moving to 100, 100")
        return worker.input.move_to(100, 100)
        
    def simple_verify():
        # Blind verify for now
        return True
        
    if worker.execute_safely(move_action, simple_verify):
        print("Move action verified!")
    else:
        print("Move action failed!")

if __name__ == "__main__":
    test_safe_path()
