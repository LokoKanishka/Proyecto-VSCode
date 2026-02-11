import os
import subprocess
import json
import sys
from pathlib import Path
from typing import Any, Dict

def ask_raw(prompt: str, timeout_sec: int = 75, retries: int = 2) -> Dict[str, Any]:
    """
    Shim function for the ChatGPT UI bridge.
    Attempts to call the external X11 scripts if they exist.
    """
    project_root = Path(__file__).resolve().parents[1]
    bridge_script = project_root / "scripts" / "chatgpt_ui_ask_x11.sh"
    
    if not bridge_script.exists():
        return {
            "ok": False,
            "error": "ChatGPT X11 Bridge script missing (scripts/chatgpt_ui_ask_x11.sh)",
            "answer_text": "",
            "answer_line": ""
        }
    
    try:
        # Attempt execution of the legacy bridge if present
        # Note: This requires a running X11 session.
        res = subprocess.run(
            [str(bridge_script), prompt],
            text=True,
            capture_output=True,
            timeout=timeout_sec
        )
        if res.returncode == 0:
            return {
                "ok": True,
                "answer_text": res.stdout.strip(),
                "answer_line": "",
                "meta": {"elapsed_ms": 0}
            }
        else:
            return {"ok": False, "error": res.stderr.strip()}
    except Exception as e:
        return {"ok": False, "error": str(e)}
