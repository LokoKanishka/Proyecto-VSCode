"""
src/workers/api.py
API Gateway & WebSocket Server.
Puente entre el EventBus y la Aleph UI (React).
"""
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import socketio
from loguru import logger

from src.core.base_worker import BaseWorker
from src.core.lucy_types import MessageType, LucyMessage, WorkerType

class APIWorker(BaseWorker):
    def __init__(self, bus):
        super().__init__("api_gateway", bus)
        self.app = FastAPI()
        self.sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins='*')
        self.socket_app = socketio.ASGIApp(self.sio, self.app)
        self.server = None
        self.port = 5052 # Puerto backend distinto a Vite (5050)
        
        # Setup Routes/Events
        self._setup_socketio()
        
        # CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_socketio(self):
        @self.sio.event
        async def connect(sid, environ):
            logger.info(f"UI Connected: {sid}")
            # Enviar estado inicial?

        @self.sio.event
        async def disconnect(sid):
            logger.info(f"UI Disconnected: {sid}")

        @self.sio.on("lucy_command")
        async def handle_command(sid, data):
            # Recibe comandos desde el frontend
            # { "type": "command", "content": "open terminal", ... }
            logger.info(f"API CMD received: {data}")
            msg = LucyMessage(
                sender="user_ui",
                receiver=data.get("receiver", WorkerType.MANAGER),
                type=MessageType.COMMAND,
                content=data.get("content", ""),
                data=data.get("data", {})
            )
            await self.bus.publish(msg)

    async def start(self):
        # No llamamos a super().start() estándar porque el subscribe es especial aquí
        # Queremos escuchar 'broadcast' y eventos específicos para empujar al frontend
        self.running = True
        logger.info(f"🌐 API Worker Starting on port {self.port}...")
        
        self.bus.subscribe("broadcast", self.push_to_frontend)
        # self.bus.subscribe(WorkerType.MANAGER, self.push_to_frontend) # Spy on manager?

        config = uvicorn.Config(self.socket_app, host="0.0.0.0", port=self.port, log_level="error")
        self.server = uvicorn.Server(config)
        
        # Correr uvicorn en el loop de asyncio
        asyncio.create_task(self.server.serve())

    async def push_to_frontend(self, message: LucyMessage):
        """Función llamada cuando el Bus recibe un broadcast."""
        try:
            # Serializar mensaje
            payload = message.model_dump()
            # Convertir enum a string si pydantic no lo hace automatico en dump
            # Emitir vía SocketIO
            await self.sio.emit("lucy_event", payload)
        except Exception as e:
            logger.error(f"Error pushing to UI: {e}")

    async def stop(self):
        if self.server:
            self.server.should_exit = True
