import json
import requests
import datetime
import os
import base64
import re
from io import BytesIO
from typing import List, Dict, Any, Optional, Generator, Set
from loguru import logger
import pyautogui
import ollama

from src.skills.base_skill import BaseSkill
from src.skills.desktop_skill_wrapper import DesktopSkillWrapper
from src.skills.research_memory import ResearchMemorySkill
from src.engine.voice_bridge import LucyVoiceBridge
from src.engine.semantic_router import SemanticRouter
from src.engine.swarm_manager import SwarmManager
from src.engine.thought_engine import Planner

SYSTEM_PROMPT = """
YOU ARE LUCY, an autonomous AI operator running locally on an RTX 5090.

MODE 1: CHAT
- If the user greets or asks a general question, reply freely via voice/text.
- VOICE TOLERANCE: The input comes from speech-to-text and may contain errors.
  Ignore grammar errors and interpret the intent (e.g., \"Te abras\" -> \"Abre\").

MODE 2: ACTION (CRITICAL)
- If the user asks to DO something: ACT FIRST, TALK LATER.
- Browser Navigation:
  - If the user asks for a specific topic on a known site (Wikipedia, Google, GitHub), open the FINAL URL directly with `launch_app` (do NOT visit homepage and search).
  - Go to URL: `perform_action(action="hotkey", text="ctrl+l")` -> `perform_action(action="type", text="<domain>")` -> `perform_action(action="hotkey", text="enter")`.
  - SCROLL DOWN / READ MORE: `perform_action(action="hotkey", text="pagedown")`.
  - SCROLL UP: `perform_action(action="hotkey", text="pageup")`.
 - App Launching:
  - Prefer direct launch: `launch_app(app_name="firefox", url="https://...")`.
  - Only use keyboard launcher as fallback.
  - If you already used `launch_app` with a URL, do NOT use `ctrl+l` again.

MODE 3: VISION
- If `capture_screen` returns a description, THAT IS YOUR REALITY.
- NEVER say "I cannot see". Use the description to answer.
- For precise clicking, use the grid overlay:
  - Step 1: `capture_screen(overlay_grid=true)` (or `grid=true`).
  - Step 2: Identify the target's grid cell (e.g., "D4").
  - Step 3: Click with `perform_action(action="move_and_click", grid="D4")`
    (or `perform_action(action="click_grid", grid_id="D4")`).
- For exact values, use `capture_region(grid="D4")` to zoom before reading.

MODE 4: RESEARCH MEMORY
- After reading a screen or a section, summarize it briefly with:
  `remember(text="...")`
- Use the accumulated memory to answer long readings.
- If the user asks to clear memory, respond: "Memoria borrada."

STRICT RULES:
- Speak Spanish.
- NO GHOST PLANNING: Do not narrate what you will do. Just call the tools.
""".strip()

class OllamaEngine:
    def __init__(self, model: Optional[str] = None, host: Optional[str] = None, vision_model: Optional[str] = None):
        self.swarm = SwarmManager(host=host, main_model=model, vision_model=vision_model)
        self.host = self.swarm.host
        self.model = self.swarm.main_model
        self.api_url = f"{self.host}/api/chat" # Usamos /api/chat para herramientas
        self.generate_url = f"{self.host}/api/generate"
        try:
            self.ollama_client = ollama.Client(host=self.host)
        except Exception:
            self.ollama_client = None
        self.planner = Planner(self.swarm, model=self.model, host=self.host)
        self.skills: Dict[str, BaseSkill] = {}
        self.router = SemanticRouter()
        self.research_memory: List[str] = []
        
        logger.info(f"🚀 OllamaEngine Monolítico inicializado (Modelo: {self.model})")
        
        # Registrar rutas básicas en el SemanticRouter
        self._setup_router()

        # Registrar habilidades de escritorio (vision + accion)
        self.desktop_skills = DesktopSkillWrapper()
        for skill in self.desktop_skills.tools():
            self.register_skill(skill)
        self.register_skill(ResearchMemorySkill(self.research_memory))

        # Modelo de vision (configurable por entorno o config.yaml)
        self.vision_model = self.swarm.vision_model

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
        self.router.register_route("memory_control", [
            "olvida todo", "olvidá todo", "olvida la memoria", "olvidá la memoria",
            "limpia memoria", "limpiá memoria", "limpia la memoria", "limpiá la memoria",
            "borra memoria", "borrá memoria", "borra la memoria", "borrá la memoria",
            "reset memoria", "reseteá memoria", "reinicia memoria", "reiniciá memoria",
            "resetear memoria", "olvida lo anterior", "olvidá lo anterior",
            "borra lo que recuerdes", "borrá lo que recuerdes",
        ])
        self.router.register_route("vision", [
            "que ves en la pantalla", "analiza lo que hay en el monitor", "describe la imagen",
            "mira la pantalla y dime", "identifica lo que ves"
        ])
        self.router.register_route("desktop_action", [
            "abrir navegador", "ejecuta la terminal", "abre la calculadora",
            "minimiza las ventanas", "toma una captura de pantalla", "abre spotify"
        ])
        self.router.register_route("complex_task", [
            "investiga sobre", "buscame precios de", "averigua el precio de",
            "entra a", "anda a", "planifica un viaje", "compara precios",
            "busca en internet", "busca en la web", "recolecta informacion",
        ])

    def _should_clear_memory(self, prompt: str) -> bool:
        text = prompt.lower()
        keywords = [
            "olvida todo", "olvidá todo", "olvida la memoria", "olvidá la memoria",
            "limpia memoria", "limpiá memoria", "limpia la memoria", "limpiá la memoria",
            "borra memoria", "borrá memoria", "borra la memoria", "borrá la memoria",
            "reset memoria", "resetear memoria", "reinicia memoria", "reiniciá memoria",
            "olvida lo anterior", "olvidá lo anterior", "borra lo que recuerdes",
            "borrá lo que recuerdes",
        ]
        return any(k in text for k in keywords)

    def _should_plan(self, prompt: str) -> bool:
        text = prompt.lower()
        keywords = [
            "investiga", "averigua", "busca", "buscame", "buscá",
            "compara", "compará", "entra a", "anda a", "planifica",
            "armame", "organiza", "recolecta", "averiguame",
        ]
        return any(k in text for k in keywords)

    def _build_system_prompt(self) -> str:
        if not self.research_memory:
            return SYSTEM_PROMPT
        memory_lines = "\n".join(f"- {item}" for item in self.research_memory)
        return f"{SYSTEM_PROMPT}\n\n### CURRENT KNOWLEDGE ###\n{memory_lines}"

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
                                                    self.swarm.set_profile("general")
                                            except Exception as e:
                                                logger.error(f"Error analizando imagen: {e}")
                                        elif func_name == "capture_region":
                                            try:
                                                payload = json.loads(result)
                                                image_path = payload.get("path")
                                                if image_path:
                                                    analysis = self._analyze_zoom(image_path)
                                                    result = (
                                                        f"Zoom realizado en {image_path}. "
                                                        f"LECTURA DE ALTA PRECISION: {analysis}"
                                                    )
                                                    self.swarm.set_profile("general")
                                            except Exception as e:
                                                logger.error(f"Error analizando zoom: {e}")
                                        elif func_name == "remember":
                                            if messages and messages[0].get("role") == "system":
                                                messages[0]["content"] = self._build_system_prompt()
                                        
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

        if intent == "memory_control" or self._should_clear_memory(prompt):
            self.research_memory.clear()
            response_text = "Memoria borrada."
            if self.tts_enabled and self.speech:
                try:
                    self.speech.say(response_text)
                except Exception as e:
                    logger.warning(f"🔇 Error al hablar: {e}")
            yield response_text
            return

        if intent == "vision" and os.getenv("LUCY_VISION_DIRECT", "0") == "1":
            yield from self._handle_vision(prompt, status_callback)
            return

        if intent == "complex_task" or self._should_plan(prompt):
            yield from self._handle_complex_task(prompt, history, status_callback)
            return

        # 2. Cognición con Herramientas
        self.swarm.set_profile("general")
        if history is None:
            history = []
        if not history or history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": self._build_system_prompt()})
        
        history.append({"role": "user", "content": prompt})
        
        if status_callback: status_callback("🗣️ Procesando...")
        allow_actions = self._should_allow_action(prompt) or intent in {"desktop_action", "system_control"}
        allow_vision = self._should_allow_vision(prompt) or intent == "vision"
        allowed_tools = set()
        if allow_actions:
            allowed_tools.add("perform_action")
            allowed_tools.add("launch_app")
        if allow_vision:
            allowed_tools.add("capture_screen")
            allowed_tools.add("capture_region")
        allowed_tools.add("remember")

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
            
            self.swarm.set_profile("vision")
            payload = {
                "model": self.vision_model,
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

    def _handle_complex_task(
        self,
        prompt: str,
        history: Optional[List[Dict[str, str]]] = None,
        status_callback=None,
    ) -> Generator[str, None, None]:
        if status_callback:
            status_callback("🧭 Planificando...")

        plan = self.planner.plan(prompt)
        if not plan:
            yield "No pude planificar esa tarea. ¿Querés intentar con una instruccion mas concreta?"
            return
        logger.info("🧭 Plan generado ({} pasos).", len(plan))

        if status_callback:
            status_callback("🛠️ Ejecutando plan...")

        for step in plan:
            tool = step.get("tool")
            args = step.get("args") or {}
            if tool not in self.skills:
                continue
            try:
                result = self.skills[tool].execute(**args)
                if tool == "capture_screen":
                    try:
                        payload = json.loads(result)
                        image_path = payload.get("path")
                        if image_path:
                            analysis = self._analyze_image(image_path)
                            result = (
                                f"Captura realizada en {image_path}. "
                                f"ANALISIS VISUAL DE LA IA: {analysis}"
                            )
                            self.swarm.set_profile("general")
                    except Exception as e:
                        logger.error(f"Error analizando imagen: {e}")
                if tool == "capture_region":
                    try:
                        payload = json.loads(result)
                        image_path = payload.get("path")
                        if image_path:
                            analysis = self._analyze_zoom(image_path)
                            result = (
                                f"Zoom realizado en {image_path}. "
                                f"LECTURA DE ALTA PRECISION: {analysis}"
                            )
                            self.swarm.set_profile("general")
                    except Exception as e:
                        logger.error(f"Error analizando zoom: {e}")
                if tool == "remember":
                    if history and history[0].get("role") == "system":
                        history[0]["content"] = self._build_system_prompt()
            except Exception as exc:
                logger.warning("Error ejecutando paso del plan ({}): {}", tool, exc)

        if history is None:
            history = []
        if not history or history[0].get("role") != "system":
            history.insert(0, {"role": "system", "content": self._build_system_prompt()})

        history.append({"role": "user", "content": prompt})
        response_tokens = []
        for token in self.chat(history, allowed_tools=set()):
            response_tokens.append(token)
            yield token

        response_text = "".join(response_tokens).strip()
        if self.tts_enabled and self.speech and response_text:
            try:
                self.speech.say(response_text)
            except Exception as e:
                logger.warning(f"🔇 Error al hablar: {e}")

    def _analyze_image(self, image_path: str) -> str:
        """Analiza una imagen local con el modelo de visión configurado."""
        if not os.path.exists(image_path):
            return "Error: La imagen capturada no existe en disco."

        self.swarm.set_profile("vision")
        prompt = (
            "SOS UN SENSOR OPTICO.\n"
            "Hay una grilla ROJA/CIAN con coordenadas A1..H10.\n"
            "PROHIBIDO: saludar, explicar, dar consejos, narrar.\n"
            "Responde con maximo 6 lineas. Formato:\n"
            "- <Etiqueta>: [A1]\n"
            "- <Etiqueta>: <valor> [A1]\n"
            "Prioriza contenido del navegador y valores numericos visibles.\n"
            "Ignora terminales/editores salvo que el usuario lo pida.\n"
            "Si ves un valor claro (precio, poblacion, etc.), ponelo como primera linea:\n"
            "- Valor: <numero> [A1]\n"
            "IMPORTANT: usa SOLO A1..H10. No uses pares numericos como [2][2]."
        )

        logger.info(f"👁️ Analizando imagen {image_path} con {self.vision_model}...")
        try:
            client = self.ollama_client or ollama
            response = client.chat(
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

    def _analyze_zoom(self, image_path: str) -> str:
        """Lee un valor puntual desde un recorte de pantalla."""
        if not os.path.exists(image_path):
            return "Error: La imagen de zoom no existe en disco."

        self.swarm.set_profile("vision")
        prompt = (
            "LEER VALOR EXACTO.\n"
            "Ignora todo lo demas y devuelve SOLO el valor tal como se ve.\n"
            "Si no hay un valor claro, responde: NOT_FOUND.\n"
        )

        logger.info(f"🔎 Analizando zoom {image_path} con {self.vision_model}...")
        try:
            client = self.ollama_client or ollama
            response = client.chat(
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
            description = self._sanitize_zoom_output(description)
            logger.info(f"🔎 Resultado zoom: {description[:100]}...")
            return description
        except Exception as e:
            logger.error(f"❌ Error en analisis zoom: {e}")
            return f"Error analizando zoom: {e}"

    @staticmethod
    def _sanitize_zoom_output(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return "NOT_FOUND"
        lowered = raw.lower()
        banned = [
            "bookmark",
            "favorito",
            "browser",
            "settings",
            "chrome",
            "edge",
            "tutorial",
        ]
        if any(word in lowered for word in banned):
            return "NOT_FOUND"
        if len(raw) > 120 and not re.search(r"\d", raw):
            return "NOT_FOUND"
        return raw

    def set_model(self, model_name):
        self.model = model_name
        self.swarm.main_model = model_name
        self.planner.model = model_name

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
