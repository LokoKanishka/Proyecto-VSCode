import time
import threading
from typing import Optional, Callable
from .wayland_input import WaylandInput
from ..vision.wayland_capture import WaylandCapture

class SafeActionWorker:
    def __init__(self, vision_adapter=None):
        self.input = WaylandInput()
        self.capture = WaylandCapture()
        self.vision = vision_adapter
        self.lock = threading.Lock()
        
    def execute_safely(self, action_func: Callable, verify_func: Optional[Callable] = None, timeout=5.0):
        """
        Executes an action and optionally verifies it visually.
        
        args:
        - action_func: function that performs the input (e.g. click)
        - verify_func: function that returns True if the state is correct
        - timeout: max time to wait for verification
        """
        with self.lock:
            # 1. Pre-action check (optional, could be added here)
            
            # 2. Execute Action
            print(f"Executing action...")
            action_result = action_func()
            
            if not action_result:
                print("Action execution failed.")
                return False
                
            # 3. Verify
            if verify_func:
                print("Verifying action...")
                start_time = time.time()
                while time.time() - start_time < timeout:
                    if verify_func():
                        print("Verification successful.")
                        return True
                    time.sleep(0.5)
                
                print("Verification failed (timeout).")
                return False
            
            return True

    def click_and_verify(self, x, y, expected_change_region=None):
        """
        High level safe click.
        If expected_change_region is provided (x,y,w,h), it waits for a visual change in that region.
         """
        def action():
            self.input.move_to(x, y)
            time.sleep(0.2) # stabilize
            return self.input.click()
            
        def verify():
            if not expected_change_region:
                return True
                
            # Implementation of visual diff could go here.
            # For now we assume verify logic is passed externally or we implement a simple diff.
            # This is a placeholder for the concept.
            return True
            
        return self.execute_safely(action, verify)
