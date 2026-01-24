from fastapi import FastAPI, Request
import uvicorn
from loguru import logger
import threading

app = FastAPI(title="Lucy Webhook Server")

# Callback global para enviar eventos al orquestador
_external_event_callback = None

@app.post("/webhook/{source}")
async def receive_webhook(source: str, request: Request):
    data = await request.json()
    logger.info(f"🌐 Webhook recibido de {source}: {data}")
    
    if _external_event_callback:
        # Formatear el mensaje para Lucy
        message = f"He recibido una notificación externa de {source}. Datos: {data}. ¿Deseas que haga algo al respecto?"
        _external_event_callback(message)
        
    return {"status": "ok", "source": source}

def start_webhook_server(callback, host="127.0.0.1", port=8000):
    global _external_event_callback
    _external_event_callback = callback
    
    logger.info(f"🚀 Iniciando servidor de Webhooks en http://{host}:{port}")
    config = uvicorn.Config(app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    
    # Ejecutar en un hilo separado para no bloquear el bucle principal
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    return server
