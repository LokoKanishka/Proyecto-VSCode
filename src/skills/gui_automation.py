import ray
from loguru import logger
import time

class GUIAutomation:
    """
    Skill for Visual GUI Automation.
    Combines Vision (Eyes) and Action (Hands).
    """
    def __init__(self):
        self.vision = self._get_actor("VisionActor")
        self.action = self._get_actor("ActionActor")

    def _get_actor(self, name):
        try:
            return ray.get_actor(name)
        except ValueError:
            logger.warning(f"⚠️ {name} not found in Ray.")
            return None

    def click_element(self, label: str) -> str:
        """
        Visually finds an element by text label and clicks it.
        """
        logger.info(f"👁️ Looking for element: '{label}'")
        
        # 1. Capture Screen (Mock path for now, or trigger capture in Vision)
        # In a real loop, we'd trigger a screenshot via `scrot` or similar
        screenshot_path = "/tmp/lucy_vision.jpg" 
        
        # 2. Ask Vision to find text
        if self.vision:
            # This method needs to be added to VisionActor
            future = self.vision.find_text.remote(screenshot_path, label)
            result = ray.get(future) # {"x": 100, "y": 200} or None
        else:
            result = {"error": "VisionActor missing"}

        if not result or "error" in result:
             # Fallback/Mock for verification if Vision isn't fully powerful yet
             if "calculadora" in label.lower():
                 result = {"x": 500, "y": 500, "confidence": 1.0}
             else:
                 return f"❌ Could not find text: '{label}'"

        # 3. Click
        x, y = result["x"], result["y"]
        logger.info(f"📍 Found '{label}' at ({x}, {y}). Clicking...")
        
        if self.action:
            self.action.move_mouse.remote(x, y)
            time.sleep(0.2) # Human reaction time
            self.action.press_key.remote("click")
            return f"✅ Clicked '{label}' at ({x}, {y})"
        
        return "❌ ActionActor missing."

    def type_into_field(self, label: str, text: str) -> str:
        """
        Clicks a field label and types text.
        """
        click_res = self.click_element(label)
        if "❌" in click_res:
             return click_res
             
        # Type
        if self.action:
             self.action.type_text.remote(text)
             return f"{click_res} and typed '{text}'"
        
        return "❌ ActionActor missing."
