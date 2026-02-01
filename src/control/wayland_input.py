import subprocess
import time
import os

class WaylandInput:
    def __init__(self):
        # Ensure ydotool is available
        try:
            subprocess.run(["ydotool", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("Warning: ydotool not found or not working. Input control will fail.")

    def move_to(self, x, y):
        """
        Move mouse to x, y absolute coordinates.
        ydotool mousemove -a x y
        """
        try:
            subprocess.run(["ydotool", "mousemove", "-a", str(x), str(y)], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error moving mouse: {e}")
            return False

    def click(self, button="left"):
        """
        Click a mouse button.
        ydotool click 0xC0 (left) or 0xC2 (right)
        Buttons: left=0xC0, right=0xC2, middle=0xC1
        """
        code = "0xC0"
        if button == "right":
            code = "0xC2"
        elif button == "middle":
            code = "0xC1"
            
        try:
            subprocess.run(["ydotool", "click", code], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error clicking mouse: {e}")
            return False

    def type_text(self, text, delay=0.05):
        """
        Type text using ydotool type.
        """
        try:
            subprocess.run(["ydotool", "type", text], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error typing text: {e}")
            return False

    def key_press(self, key_combo):
        """
        Press a key combination using ydotool key.
        combo example: 'ctrl+c', 'alt+tab'
        """
        # ydotool key key_code:state ...
        # This is a basic implementation, properly mapping strings to keycodes 
        # is complex and usually handled by the tool itself mostly.
        # ydotool 'key' command accepts strings like '104:1 104:0' (Enter down up)
        # or simplified syntax depending on version.
        try:
            subprocess.run(["ydotool", "key", key_combo], check=True)
            return True
        except subprocess.CalledProcessError as e:
            print(f"Error pressing key: {e}")
            return False
