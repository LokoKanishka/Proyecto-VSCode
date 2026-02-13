"""
LUCY ALEPH ACTION - Actor de Interacción con Host (File-IPC).
Ubicación: src/core/action_actor.py
"""
import ray
import json
import uuid
import os
import asyncio
from loguru import logger
from typing import Dict, Any

IPC_ROOT = "data/ipc"
INBOX_DIR = os.path.join(IPC_ROOT, "inbox")
OUTBOX_DIR = os.path.join(IPC_ROOT, "outbox")

@ray.remote(namespace="lucy")
class ActionActor:
    def __init__(self):
        os.makedirs(INBOX_DIR, exist_ok=True)
        os.makedirs(OUTBOX_DIR, exist_ok=True)
        logger.info("⚔️ ACTION ACTOR (File-IPC Bridge) initialized.")

    async def execute_action(self, action_type: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Envía una acción al agente del host y espera el resultado."""
        cmd_id = str(uuid.uuid4())
        payload = {
            "id": cmd_id,
            "type": action_type,
            "params": params,
            "timestamp": os.times().elapsed
        }
        
        # 1. Escribir comando en /inbox (Atomic write pattern)
        cmd_path = os.path.join(INBOX_DIR, f"{cmd_id}.json")
        tmp_path = cmd_path + ".tmp"
        
        with open(tmp_path, "w") as f:
            json.dump(payload, f)
        os.rename(tmp_path, cmd_path)
        logger.debug(f"Action dispatched: {action_type} [{cmd_id}]")
        
        # 2. Esperar respuesta en /outbox con timeout
        response_path = os.path.join(OUTBOX_DIR, f"{cmd_id}.result.json")
        
        for _ in range(50): # 5 segundos timeout (100ms polling)
            if os.path.exists(response_path):
                try:
                    with open(response_path, "r") as f:
                        result = json.load(f)
                    os.remove(response_path) # Limpieza
                    return result
                except Exception as e:
                    logger.error(f"Error reading result for {cmd_id}: {e}")
                    return {"status": "error", "message": str(e)}
            
            await asyncio.sleep(0.1)
            
        logger.warning(f"Action timed out: {cmd_id}")
        return {"status": "timeout", "message": "Host agent did not respond"}

    async def health_check(self):
        return {"status": "ALIVE", "ipc_path": IPC_ROOT}
