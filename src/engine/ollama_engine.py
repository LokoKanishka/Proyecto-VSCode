import json
import requests
import datetime
import os
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional, Generator
from loguru import logger
import pyautogui

from src.skills.base_skill import BaseSkill
from src.engine.semantic_router import SemanticRouter

class OllamaEngine:
    def __init__(self, model="llama3.1", host="http://localhost:11434"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/chat" # Usamos /api/chat para herramientas
        self.generate_url = f"{host}/api/generate"
        self.skills: Dict[str, BaseSkill] = {}
        self.router = SemanticRouter()
        
        logger.info(f"🚀 OllamaEngine Monolítico inicializado (Modelo: {self.model})")
        
        # Registrar rutas básicas en el SemanticRouter
        self._setup_router()

    def _setup_router(self):
        """Configura las intenciones básicas para el enrutamiento rápido."""
        # Aumentamos el umbral para ser más selectivos
        self.router.threshold = 0.6
        
        self.router.register_route("system_control", [
            "subir volumen", "bajar volumen", "silencio", "mute",
            "apagar", "reiniciar", "cerrar todo", "maximizar ventana"
        ])
        self.router.register_route("vision", [
            "que ves en la pantalla", "analiza lo que hay en el monitor", "describe la imagen",
            "mira la pantalla y dime", "identifica lo que ves"
        ])
        self.router.register_route("desktop_action", [
            "abrir navegador", "ejecuta la terminal", "abre la calculadora",
            "minimiza las ventanas", "toma una captura de pantalla", "abre spotify"
        ])

    def register_skill(self, skill: BaseSkill):
        """Registra una habilidad para que el LLM pueda usarla."""
        self.skills[skill.name] = skill
        logger.info(f"🛠️ Habilidad registrada: {skill.name}")

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Devuelve las definiciones de herramientas en formato Ollama."""
        return [
            {
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.parameters,
                }
            } for skill in self.skills.values()
        ]

    def chat(self, messages: List[Dict[str, str]], stream: bool = True) -> Generator[str, None, None]:
        """Bucle de chat principal con soporte para herramientas."""
        tools = self.get_tool_definitions()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "tools": tools,
            "options": {"temperature": 0.3}
        }

        try:
            if stream:
                full_response = ""
                with requests.post(self.api_url, json=payload, stream=True) as response:
                    response.raise_for_status()
                    for line in response.iter_lines():
                        if not line: continue
                        body = json.loads(line.decode("utf-8"))
                        
                        if "message" in body:
                            msg = body["message"]
                            
                            # Manejar llamadas a herramientas (Ollama suele enviarlas al final o en un bloque)
                            if "tool_calls" in msg:
                                for tool_call in msg["tool_calls"]:
                                    func_name = tool_call["function"]["name"]
                                    args = tool_call["function"]["arguments"]
                                    
                                    # Ejecutar la herramienta
                                    if func_name in self.skills:
                                        result = self.skills[func_name].execute(**args)
                                        
                                        # Añadir llamada y resultado al historial
                                        messages.append(msg)
                                        messages.append({
                                            "role": "tool",
                                            "content": result
                                        })
                                        
                                        # Recursión para que el LLM procese el resultado
                                        yield from self.chat(messages, stream=True)
                                        return
                            
                            content = msg.get("content", "")
                            if content:
                                full_response += content
                                yield content
            else:
                res = requests.post(self.api_url, json=payload)
                res.raise_for_status()
                # Implementar lógica no-stream si es necesario
                pass

        except Exception as e:
            logger.error(f"Error en OllamaEngine.chat: {e}")
            yield f"Error de inferencia: {str(e)}"

    def generate_response(self, prompt: str, history: List[Dict[str, str]] = None, status_callback=None):
        """
        Punto de entrada compatible con el flujo actual.
        Implementa el ciclo: Route -> Cognition -> Action.
        """
        if status_callback: status_callback("🧠 Analizando intención...")
        
        # 1. Enrutamiento Rápido
        intent = self.router.route(prompt)
        logger.info(f"Intención detectada por Router: {intent}")

        if intent == "vision":
            yield from self._handle_vision(prompt, status_callback)
            return

        # 2. Cognición con Herramientas
        if history is None:
            history = []
        
        history.append({"role": "user", "content": prompt})
        
        if status_callback: status_callback("🗣️ Procesando...")
        yield from self.chat(history)

    def _handle_vision(self, prompt: str, status_callback=None) -> Generator[str, None, None]:
        """Lógica de visión (LLaVA) integrada."""
        if status_callback: status_callback("👁️ Capturando pantalla...")
        
        try:
            screenshot = pyautogui.screenshot()
            buffered = BytesIO()
            screenshot.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            # Usamos un prompt de sistema duro para visión
            vision_prompt = f"Describe detalladamente lo que ves en la pantalla relacionado con: {prompt}. Responde solo en español."
            
            payload = {
                "model": "llava", 
                "prompt": vision_prompt,
                "images": [img_str],
                "stream": True,
                "options": {"temperature": 0.1} 
            }
            
            if status_callback: status_callback("🧠 Analizando imagen...")
            
            with requests.post(self.generate_url, json=payload, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line: continue
                    body = json.loads(line.decode('utf-8'))
                    yield body.get('response', '')
                    
        except Exception as e:
            logger.error(f"Error en visión: {e}")
            yield f"Error al intentar ver la pantalla: {str(e)}"

    def set_model(self, model_name):
        self.model = model_name

# --- COMPATIBILITY WRAPPER ---
_global_engine = None

def process_intent(prompt: str) -> str:
    """
    Wrapper de compatibilidad para el flujo de Windows.
    Utiliza el motor avanzado para procesar una entrada de texto.
    """
    global _global_engine
    if _global_engine is None:
        try:
            from src.skills.web_search import WebSearchSkill
            from src.skills.youtube_skill import YoutubeSkill
            from src.skills.system_control import SystemControlSkill
            
            _global_engine = OllamaEngine()
            # Registrar habilidades por defecto
            _global_engine.register_skill(WebSearchSkill())
            _global_engine.register_skill(YoutubeSkill())
            _global_engine.register_skill(SystemControlSkill())
        except Exception as e:
            return f"Error iniciando el motor: {e}"
    
    # Consumir el generador de respuesta
    response_tokens = []
    try:
        for token in _global_engine.generate_response(prompt):
            response_tokens.append(token)
    except Exception as e:
        return f"Error procesando la intención: {e}"
    
    return "".join(response_tokens)
