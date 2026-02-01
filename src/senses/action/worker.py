import ray
import asyncio
from loguru import logger
import time
import random
import math
import os
import subprocess
import ast

# Human-like mouse movement logic
def bezier_point(t, P0, P1, P2):
    """Quadratic Bezier curve."""
    return (1 - t)**2 * P0 + 2 * (1 - t) * t * P1 + t**2 * P2

@ray.remote
class ActionActor:
    """
    Ray Actor managing the 'Hand' (Mouse/Keyboard).
    Uses xdotool for atomic actions (works in X11/XWayland).
    """
    def __init__(self):
        logger.info("👋 ActionActor initializing...")
        self.safe_mode = True
        
        # Check connection (xdotool)
        try:
             subprocess.run(["xdotool", "version"], capture_output=True, check=True)
             logger.info("✅ xdotool connected.")
        except Exception as e:
             logger.warning(f"⚠️ xdotool check failed: {e}. Running in MOCK mode.")

        # Initialize Skills
        from src.skills.business_tools import BusinessTools
        self.business_tools = BusinessTools()
        
        from src.skills.gui_automation import GUIAutomation
        self.gui_automation = GUIAutomation()

    async def execute_plan(self, plan: list) -> str:
        """
        Executes a list of action strings.
        """
        logger.info(f"👋 Executing plan with {len(plan)} steps.")
        results = []
        for step in plan:
            logger.info(f"👉 Performing: {step}")
            
            # Simple parser for the plan steps
            if step.startswith("Tool:"):
                # Handle Tool Execution
                # Format: Tool: ClassName.method_name(args)
                try:
                    # Remove "Tool: " prefix
                    cmd = step.replace("Tool:", "").strip()
                    # e.g. ShippingCalculator.calculate_shipping(destination='Madrid', weight_kg=10)
                    
                    method_name = cmd.split("(")[0].split(".")[-1].strip()
                    args_str = cmd.split("(", 1)[1].rsplit(")", 1)[0]
                    
                    # Robust parsing using AST
                    pos_args = []
                    kw_args = {}
                    
                    if args_str.strip():
                        tree = ast.parse(f"func({args_str})")
                        call_node = tree.body[0].value
                        
                        # Extract Positional Args
                        for arg in call_node.args:
                            if isinstance(arg, ast.Constant):
                                pos_args.append(arg.value)
                            elif isinstance(arg, ast.Num): # Python < 3.8
                                pos_args.append(arg.n)
                            elif isinstance(arg, ast.Str): # Python < 3.8
                                pos_args.append(arg.s)
                                
                        # Extract Keyword Args
                        for keyword in call_node.keywords:
                            val = None
                            if isinstance(keyword.value, ast.Constant):
                                val = keyword.value.value
                            kw_args[keyword.arg] = val
                            
                    # Find method on BusinessTools instance
                    if hasattr(self.business_tools, method_name):
                        func = getattr(self.business_tools, method_name)
                        res = func(*pos_args, **kw_args)
                        results.append(f"Tool Output ({method_name}): {res}")
                    elif hasattr(self.gui_automation, method_name):
                        func = getattr(self.gui_automation, method_name)
                        res = func(*pos_args, **kw_args)
                        results.append(f"Tool Output ({method_name}): {res}")
                    else:
                        results.append(f"Error: Tool method '{method_name}' not found.")
                        
                except Exception as e:
                    logger.error(f"Tool Execution Failed: {e}")
                    results.append(f"Tool Error: {e}")

            elif "Type" in step:
                # "Action: Type 'terminal'"
                try:
                    text = step.split("'")[1]
                    await self.type_text(text)
                except IndexError:
                    logger.warning(f"Could not parse text from: {step}") 

            elif "Enter" in step or "Press" in step:
                await self.press_key("Return")

            elif "Application Launcher" in step:
                # "Control: Open Application Launcher (Super Key)"
                await self.press_key("super")
            
            await asyncio.sleep(0.5) 
            results.append(f"Done: {step}")
            
        return "\n".join(results)

    async def move_mouse(self, x: int, y: int, duration: float = 0.5):
        """
        Moves mouse to (x, y) using a human-like Bezier curve.
        """
        logger.info(f"🖱️ Moving mouse to ({x}, {y})")
        # xdotool mousemove x y
        subprocess.run(["xdotool", "mousemove", str(x), str(y)])
        return True

    async def type_text(self, text: str):
        logger.info(f"⌨️ Typing: {text}")
        subprocess.run(["xdotool", "type", "--delay", "50", text])
        return True

    async def press_key(self, key: str):
        logger.info(f"⌨️ Pressing: {key}")
        subprocess.run(["xdotool", "key", key])
        return True
