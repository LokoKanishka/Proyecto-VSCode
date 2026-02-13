"""
Script para disparar la apertura de una terminal a través de LUCY ALEPH ACTION.
"""
import ray
import asyncio
from loguru import logger

async def trigger():
    try:
        # Conectar al clúster existente
        ray.init(address="auto", namespace="lucy", ignore_reinit_error=True)
        
        # Obtener el actor de acción
        action_actor = ray.get_actor("ActionActor")
        
        logger.info("🚀 Solicitando apertura de terminal y saludo...")
        
        # 1. Abrir terminal
        await action_actor.execute_action.remote(
            action_type="terminal_cmd",
            params={"command": "gnome-terminal"}
        )
        
        # 2. Esperar a que la ventana abra
        await asyncio.sleep(1.5)
        
        # 3. Escribir saludo
        result = await action_actor.execute_action.remote(
            action_type="type_text",
            params={"text": "echo 'LUCY ALEPH UI: CONEXION MANUAL ESTABLECIDA'\n"}
        )
        
        if result.get("status") == "success":
            logger.success("✅ Terminal abierta y saludo enviado.")
        else:
            logger.error(f"❌ Fallo en la interacción: {result}")
            
    except Exception as e:
        logger.error(f"Error en el disparo: {e}")

if __name__ == "__main__":
    asyncio.run(trigger())
