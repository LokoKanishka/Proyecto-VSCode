import subprocess
import os
import time

class WaylandCapture:
    def __init__(self, output_dir="screenshots"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def capture_full(self, filename=None):
        """
        Captures the full screen using grim.
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"screenshot_{timestamp}.png"
        
        path = os.path.join(self.output_dir, filename)
        
        try:
            subprocess.run(["grim", path], check=True)
            return path
        except subprocess.CalledProcessError as e:
            print(f"Error capturing screen: {e}")
            return None

    def capture_region(self, x, y, w, h, filename=None):
        """
        Captures a region using grim -g.
        """
        if filename is None:
            timestamp = int(time.time())
            filename = f"region_{timestamp}.png"
            
        path = os.path.join(self.output_dir, filename)
        geometry = f"{x},{y} {w}x{h}"
        
        try:
            subprocess.run(["grim", "-g", geometry, path], check=True)
            return path
        except subprocess.CalledProcessError as e:
            print(f"Error capturing region: {e}")
            return None
