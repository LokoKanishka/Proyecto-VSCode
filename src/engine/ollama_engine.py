import json
import requests
import datetime
import os
import base64
from io import BytesIO
from typing import List, Dict, Any, Optional, Generator, Set
from loguru import logger
import pyautogui
import ollama

from src.skills.base_skill import BaseSkill
from src.skills.desktop_skill_wrapper import DesktopSkillWrapper
from src.engine.voice_bridge import LucyVoiceBridge
from src.engine.semantic_router import SemanticRouter

SYSTEM_PROMPT = """
YOU ARE LUCY, an autonomous AI operator running locally on an RTX 5090.

MODE 1: CHAT
- If the user greets or asks a general question, reply freely via voice/text.
- VOICE TOLERANCE: The input comes from speech-to-text and may contain errors.
  Ignore grammar errors and interpret the intent (e.g., \"Te abras\" -> \"Abre\").

MODE 2: ACTION (CRITICAL)
- If the user asks to DO something: ACT FIRST, TALK LATER.
- Browser Navigation:
  - Go to URL: `perform_action(action="hotkey", text="ctrl+l")` -> `perform_action(action="type", text="<domain>")` -> `perform_action(action="hotkey", text="enter")`.
  - SCROLL DOWN / READ MORE: `perform_action(action="hotkey", text="pagedown")`.
  - SCROLL UP: `perform_action(action="hotkey", text="pageup")`.
- App Launching:
  - Call `perform_action` with action="hotkey" and text="winleft".
  - Call `perform_action` with action="type" and text="<app name>".
  - Call `perform_action` with action="hotkey" and text="enter".

MODE 3: VISION
- If `capture_screen` returns a description, THAT IS YOUR REALITY.
- NEVER say "I cannot see". Use the description to answer.

STRICT RULES:
- Speak Spanish.
- NO GHOST PLANNING: Do not narrate what you will do. Just call the tools.
""".strip()

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

        # Registrar habilidades de escritorio (vision + accion)
        self.desktop_skills = DesktopSkillWrapper()
        for skill in self.desktop_skills.tools():
            self.register_skill(skill)

        # Modelo de vision (configurable por entorno)
        self.vision_model = os.getenv("LUCY_VISION_MODEL", "llava:latest")

        # Inicializar voz (Mimic3)
        self.tts_enabled = os.getenv("LUCY_TTS_ENABLED", "1") == "1"
        try:
            self.speech = LucyVoiceBridge()
            logger.info("🔊 Voz conectada (LucyVoiceBridge)")
        except Exception as e:
            logger.warning(f"🔇 No se pudo iniciar la voz: {e}")
            self.speech = None

    def _should_allow_action(self, prompt: str) -> bool:
        text = prompt.lower()
        keywords = [
            "abre", "abrir", "abri", "abrí", "open", "launch", "inicia",
            "entra", "ir a", "anda a", "navega", "visit", "visita",
            "click", "clic", "haz clic", "hace clic", "presiona", "apreta",
            "escribi", "escribe", "tipea", "type", "hotkey", "atajo",
            "baja", "bajar", "sube", "subir", "arriba", "abajo",
            "scroll", "avpág", "avpag", "re pág", "repag", "page down", "page up",
            "sigue leyendo", "leer mas", "leé mas", "lee más", "más abajo",
        ]
        return any(k in text for k in keywords)

    def _should_allow_vision(self, prompt: str) -> bool:
        text = prompt.lower()
        keywords = [
            "mira", "mirá", "mirar", "ver", "ves", "pantalla", "screen",
            "captura", "screenshot", "foto", "lee", "leé", "leer", "read",
        ]
        return any(k in text for k in keywords)

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

    def get_tool_definitions(self, allowed_names: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
        """Devuelve las definiciones de herramientas en formato Ollama."""
        skills = list(self.skills.values())
        if allowed_names is not None:
            skills = [skill for skill in skills if skill.name in allowed_names]
        return [
            {
                "type": "function",
                "function": {
                    "name": skill.name,
                    "description": skill.description,
                    "parameters": skill.parameters,
                }
            } for skill in skills
        ]

    def chat(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
        tool_iterations: int = 0,
        max_tool_iterations: int = 3,
        allowed_tools: Optional[Set[str]] = None,
    ) -> Generator[str, None, None]:
        """Bucle de chat principal con soporte para herramientas."""
        tools = self.get_tool_definitions(allowed_tools)
        
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
                                if tool_iterations >= max_tool_iterations:
                                    logger.warning(
                                        "Limite de herramientas alcanzado (%s). Cortando loop.",
                                        max_tool_iterations,
                                    )
                                    yield (
                                        "Se alcanzo el limite de acciones en este turno. "
                                        "Dime si queres que lo intente de nuevo."
                                    )
                                    return
                                for tool_call in msg["tool_calls"]:
                                    func_name = tool_call["function"]["name"]
                                    args = tool_call["function"]["arguments"]
                                    
                                    if allowed_tools is not None and func_name not in allowed_tools:
                                        logger.warning(
                                            "Tool '%s' bloqueada por politica para este turno.",
                                            func_name,
                                        )
                                        yield "No es necesario ejecutar herramientas para responder."
                                        return

                                    # Ejecutar la herramienta
                                    if func_name in self.skills:
                                        result = self.skills[func_name].execute(**args)

                                        if func_name == "capture_screen":
                                            try:
                                                payload = json.loads(result)
                                                image_path = payload.get("path")
                                                if image_path:
                                                    analysis = self._analyze_image(image_path)
                                                    result = (
                                                        f"Captura realizada en {image_path}. "
                                                        f"ANALISIS VISUAL DE LA IA: {analysis}"
                                                    )
                                            except Exception as e:
                                                logger.error(f"Error analizando imagen: {e}")
                                        
                                        # Añadir llamada y resultado al historial
                                        messages.append(msg)
                                        messages.append({
                                            "role": "tool",
                                            "content": result
                                        })
                                        
                                        # Recursión para que el LLM procese el resultado
                                        yield from self.chat(
                                            messages,
                                            stream=True,
                                            tool_iterations=tool_iterations + 1,
                                            max_tool_iterations=max_tool_iterations,
                                            allowed_tools=allowed_tools,
                                        )
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

        if intent == "vision" and os.getenv("LUCY_VISION_DIRECT", "0") == "1":
            yield from self._handle_vision(prompt, status_callback)
            return

        # 2. Cognición con Herramientas
        if history is None:
            history = []
        if not history or history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
        
        history.append({"role": "user", "content": prompt})
        
        if status_callback: status_callback("🗣️ Procesando...")
        allow_actions = self._should_allow_action(prompt) or intent in {"desktop_action", "system_control"}
        allow_vision = self._should_allow_vision(prompt) or intent == "vision"
        allowed_tools = set()
        if allow_actions:
            allowed_tools.add("perform_action")
        if allow_vision:
            allowed_tools.add("capture_screen")

        response_tokens = []
        for token in self.chat(history, allowed_tools=allowed_tools):
            response_tokens.append(token)
            yield token

        response_text = "".join(response_tokens).strip()
        if self.tts_enabled and self.speech and response_text:
            try:
                self.speech.say(response_text)
            except Exception as e:
                logger.warning(f"🔇 Error al hablar: {e}")

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

    def _analyze_image(self, image_path: str) -> str:
        """Analiza una imagen local con el modelo de visión configurado."""
        if not os.path.exists(image_path):
            return "Error: La imagen capturada no existe en disco."

        prompt = (
            "ACT AS A UI NAVIGATOR.\n"
            "Analyze the screenshot. There is a RED/CYAN GRID overlaid.\n"
            "- Columns: A, B, C, D...\n"
            "- Rows: 1, 2, 3, 4...\n\n"
            "YOUR TASK: Identify key elements and their GRID COORDINATES.\n"
            "FORMAT: \"Element Name: [Coordinate]\"\n\n"
            "Example:\n"
            "- Terminal Window: [C4]\n"
            "- VS Code Sidebar: [A2]\n"
            "- Web Browser: [F5]\n\n"
            "Describe what is open and WHERE it is using the grid."
        )

        logger.info(f"👁️ Analizando imagen {image_path} con {self.vision_model}...")
        try:
            response = ollama.chat(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_path],
                    }
                ],
            )
            description = response["message"]["content"]
            logger.info(f"👁️ Resultado visual: {description[:100]}...")
            return description
        except Exception as e:
            logger.error(f"❌ Error en analisis visual: {e}")
            return f"Error analizando la imagen: {e}"

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
