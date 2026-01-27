import json
import requests
import datetime
import os
import base64
import re
import unicodedata
import time
from io import BytesIO
from typing import List, Dict, Any, Optional, Generator, Set
from loguru import logger
import pyautogui
import ollama
from PIL import Image

from src.skills.base_skill import BaseSkill
from src.skills.desktop_skill_wrapper import DesktopSkillWrapper
from src.skills.research_memory import ResearchMemorySkill
from src.engine.voice_bridge import LucyVoiceBridge
from src.engine.semantic_router import SemanticRouter
from src.engine.swarm_manager import SwarmManager
from src.engine.thought_engine import Planner, ThoughtEngine, ThoughtNode

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
        timeout_env = os.getenv("LUCY_OLLAMA_TIMEOUT", "30")
        try:
            self.ollama_timeout_s = float(timeout_env)
        except ValueError:
            self.ollama_timeout_s = 30.0

        self.swarm = SwarmManager(
            host=host,
            main_model=model,
            vision_model=vision_model,
            timeout_s=self.ollama_timeout_s,
        )
        self.host = self.swarm.host
        self.model = self.swarm.main_model
        self.api_url = f"{self.host}/api/chat" # Usamos /api/chat para herramientas
        self.generate_url = f"{self.host}/api/generate"
        try:
            self.ollama_client = ollama.Client(host=self.host, timeout=self.ollama_timeout_s)
        except Exception:
            self.ollama_client = None
        self.planner = Planner(self.swarm, model=self.model, host=self.host, timeout_s=self.ollama_timeout_s)
        self.brain = ThoughtEngine(self.swarm, model=self.model, host=self.host, timeout_s=self.ollama_timeout_s)
        self.skills: Dict[str, BaseSkill] = {}
        self.router = SemanticRouter()
        self.research_memory: List[str] = []
        self.max_tool_iterations = int(os.getenv("LUCY_MAX_TOOL_ITERATIONS", "8"))
        
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
        text = self._normalize_text(prompt.lower())
        keywords = [
            "abre", "abrir", "abri", "abrí", "open", "launch", "inicia",
            "entra", "ir a", "anda a", "navega", "visit", "visita",
            "click", "clic", "haz clic", "hace clic", "presiona", "apreta",
            "escribi", "escribe", "tipea", "type", "hotkey", "atajo",
            "baja", "bajar", "sube", "subir", "arriba", "abajo",
            "scroll", "avpág", "avpag", "re pág", "repag", "page down", "page up",
            "sigue leyendo", "leer mas", "leé mas", "lee más", "más abajo",
        ]
        return any(self._normalize_text(k) in text for k in keywords)

    def _should_allow_vision(self, prompt: str) -> bool:
        text = self._normalize_text(prompt.lower())
        keywords = [
            "mira", "mirá", "mirar", "ver", "ves", "pantalla", "screen",
            "captura", "screenshot", "foto", "lee", "leé", "leer", "read",
        ]
        return any(self._normalize_text(k) in text for k in keywords)

    @staticmethod
    def _normalize_text(text: str) -> str:
        normalized = unicodedata.normalize("NFD", text or "")
        return "".join(ch for ch in normalized if not unicodedata.combining(ch))

    def _setup_router(self):
        """Configura las intenciones básicas para el enrutamiento rápido."""
        # Aumentamos el umbral para ser más selectivos
        try:
            self.router.threshold = float(os.getenv("LUCY_ROUTER_THRESHOLD", "0.55"))
        except ValueError:
            self.router.threshold = 0.55
        
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
            "planificame un viaje", "planificá un viaje", "planeame un viaje",
            "armame una rutina", "armame una rutina de", "armá una rutina de",
            "quiero que busques y luego", "investigá sobre", "investiga y guardalo",
            "investigá sobre y guardalo", "busca y guardalo",
            "continuá en", "continua en", "seguí en", "segui en",
            "continuá en skyscanner", "continua en skyscanner", "seguí en skyscanner", "segui en skyscanner",
            "completa los campos", "completá los campos", "rellena los campos", "llená el formulario",
            "buscá vuelos", "busca vuelos", "buscá vuelos en", "busca vuelos en",
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
            "planificame", "planificá", "planea", "planeá", "planeame",
            "armame", "armá", "organiza", "organizá", "recolecta", "averiguame",
            "continuá", "continua", "seguí", "segui", "completa", "completá", "rellena", "llená",
            "precio", "valor", "exacto", "bitcoin", "cotizacion", "cotización",
        ]
        return any(k in text for k in keywords)

    def _build_system_prompt(self) -> str:
        if not self.research_memory:
            return SYSTEM_PROMPT
        memory_lines = "\n".join(f"- {item}" for item in self.research_memory)
        return f"{SYSTEM_PROMPT}\n\n### CURRENT KNOWLEDGE ###\n{memory_lines}"

    @staticmethod
    def _precision_requested(prompt: str) -> bool:
        lowered = (prompt or "").lower()
        keywords = ["precio", "valor", "exacto", "cuanto", "cuánto", "poblacion", "población"]
        return any(k in lowered for k in keywords)

    @staticmethod
    def _extract_cell_from_analysis(text: str) -> Optional[str]:
        if not text:
            return None
        match = re.search(r"\[([A-H](?:10|[1-9]))\]", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()
        return None

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
            "options": {"temperature": 0.3}
        }
        if tools:
            payload["tools"] = tools

        try:
            if stream:
                full_response = ""
                with requests.post(
                    self.api_url,
                    json=payload,
                    stream=True,
                    timeout=self.ollama_timeout_s,
                ) as response:
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
                                    content = (msg.get("content") or "").strip()
                                    if content:
                                        yield content
                                    else:
                                        fallback_messages = list(messages)
                                        fallback_messages.append(
                                            {
                                                "role": "system",
                                                "content": "Provide a text summary only. Do NOT use tools.",
                                            }
                                        )
                                        try:
                                            fallback_payload = {
                                                "model": self.model,
                                                "messages": fallback_messages,
                                                "stream": False,
                                                "options": {"temperature": 0.3},
                                            }
                                            res = requests.post(
                                                self.api_url,
                                                json=fallback_payload,
                                                timeout=self.ollama_timeout_s,
                                            )
                                            res.raise_for_status()
                                            data = res.json()
                                            fallback_content = (
                                                data.get("message", {}).get("content", "").strip()
                                            )
                                            if fallback_content:
                                                yield fallback_content
                                            else:
                                                yield (
                                                    "Intenté usar una herramienta pero estoy en modo solo texto. "
                                                    f"Aquí está el resumen: {content}"
                                                )
                                        except Exception as exc:
                                            logger.warning(
                                                "Fallback de resumen en texto falló: {}",
                                                exc,
                                            )
                                            yield (
                                                "Intenté usar una herramienta pero estoy en modo solo texto. "
                                                f"Aquí está el resumen: {content}"
                                            )
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
                res = requests.post(self.api_url, json=payload, timeout=self.ollama_timeout_s)
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
        for token in self.chat(
            history,
            allowed_tools=allowed_tools,
            max_tool_iterations=self.max_tool_iterations,
        ):
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
            
            with requests.post(
                self.generate_url,
                json=payload,
                stream=True,
                timeout=self.ollama_timeout_s,
            ) as response:
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
            status_callback("🧭 Pensando...")

        if history is None:
            history = []

        precision_failed = False
        executed_any = False
        last_step: Optional[tuple[str, Dict[str, Any]]] = None
        last_result: Optional[str] = None
        force_precision = self._precision_requested(prompt)
        task_state = f"User Request: {prompt}"
        if self.research_memory:
            task_state += f"\nMemory: {' | '.join(self.research_memory[-5:])}"

        for step_count in range(self.max_tool_iterations):
            root = ThoughtNode(
                id=f"root-{step_count}",
                parent=None,
                plan_step={},
                state_snapshot=task_state,
                score=1.0,
                depth=0,
            )
            best_node = self.brain.search_dfs(root)
            if not best_node or not best_node.plan_step:
                logger.error("El cerebro se quedó en blanco.")
                break

            tool = best_node.plan_step.get("tool")
            args = best_node.plan_step.get("args") or {}
            if tool not in self.skills:
                logger.warning("Tool desconocida en ToT: {}", tool)
                task_state += f"\nStep proposed: {tool} (no disponible)."
                continue

            executed_any = True
            if status_callback:
                status_callback(f"🛠️ Ejecutando: {tool}...")

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
                            if force_precision:
                                target_cell = self._extract_cell_from_analysis(analysis)
                                if not target_cell:
                                    time.sleep(1.0)
                                    retry = self.skills["capture_screen"].execute(grid=True)
                                    try:
                                        retry_payload = json.loads(retry)
                                        retry_path = retry_payload.get("path")
                                        if retry_path:
                                            retry_analysis = self._analyze_image(retry_path)
                                            target_cell = self._extract_cell_from_analysis(retry_analysis)
                                    except Exception:
                                        target_cell = None
                                if target_cell:
                                    zoom_result = self.skills["capture_region"].execute(
                                        grid=target_cell
                                    )
                                    try:
                                        zoom_payload = json.loads(zoom_result)
                                        zoom_path = zoom_payload.get("path")
                                        if zoom_path:
                                            zoom_analysis = self._analyze_zoom(zoom_path)
                                            result = (
                                                f"{result} "
                                                f"ZOOM AUTOMATICO: {zoom_analysis}"
                                            )
                                            self.swarm.set_profile("general")
                                            if (
                                                zoom_analysis
                                                and zoom_analysis != "NOT_FOUND"
                                                and re.search(r"\d", zoom_analysis)
                                            ):
                                                logger.info(
                                                    "✅ Dato numérico obtenido. Finalizando tarea."
                                                )
                                                final_response = (
                                                    f"El valor exacto es: {zoom_analysis}"
                                                )
                                                if self.tts_enabled and self.speech:
                                                    try:
                                                        self.speech.say(final_response)
                                                    except Exception as e:
                                                        logger.warning(
                                                            f"🔇 Error al hablar: {e}"
                                                        )
                                                yield final_response
                                                return
                                    except Exception as zoom_exc:
                                        logger.warning(
                                            "Error procesando zoom automatico: %s", zoom_exc
                                        )
                                else:
                                    precision_failed = True
                                    break
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
                            if analysis and analysis != "NOT_FOUND" and re.search(r"\d", analysis):
                                logger.info("✅ Dato numérico obtenido. Finalizando tarea.")
                                final_response = f"El valor exacto es: {analysis}"
                                if self.tts_enabled and self.speech:
                                    try:
                                        self.speech.say(final_response)
                                    except Exception as e:
                                        logger.warning(f"🔇 Error al hablar: {e}")
                                yield final_response
                                return
                    except Exception as e:
                        logger.error(f"Error analizando zoom: {e}")
                if tool == "remember":
                    if history and history[0].get("role") == "system":
                        history[0]["content"] = self._build_system_prompt()
            except Exception as exc:
                logger.warning("Error ejecutando paso del plan ({}): {}", tool, exc)
                task_state += f"\nStep failed: {tool}. Error: {exc}"
                continue

            last_step = (tool, args)
            last_result = result

            task_state += f"\nStep executed: {tool}. Result: {result}"
            if tool == "perform_action":
                action_name = str(args.get("action") or "").lower()
                if action_name in {"move_and_click", "click", "click_grid"}:
                    task_state += "\n[FOCUS OK]"
            if tool in {"launch_app", "perform_action"}:
                wait_s = float(os.getenv("LUCY_UI_WAIT_S", "2.0"))
                time.sleep(max(0.0, wait_s))
                vision_desc = self._capture_and_describe_screen()
                if vision_desc:
                    task_state += f"\n[SCREEN UPDATE]: {vision_desc}"
            if len(task_state) > 5000:
                task_state = task_state[-5000:]

        if precision_failed:
            response_text = "No pude leer el valor con claridad. ¿Querés que lo reintente?"
            if self.tts_enabled and self.speech:
                try:
                    self.speech.say(response_text)
                except Exception as e:
                    logger.warning(f"🔇 Error al hablar: {e}")
            yield response_text
            return

        if not executed_any:
            yield "No pude planificar esa tarea. ¿Querés intentar con una instruccion mas concreta?"
            return
        response_text = self._fallback_complex_summary(
            prompt=prompt,
            last_step=last_step,
            last_result=last_result,
        )
        if response_text:
            if self.tts_enabled and self.speech:
                try:
                    self.speech.say(response_text)
                except Exception as e:
                    logger.warning(f"🔇 Error al hablar: {e}")
            yield response_text
            return

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
            "Si ves campos de formulario (Origen/De, Destino/A, Salida/Regreso, Buscar), "
            "reportalos con su coordenada. Ejemplo: \"- Destino: [C3]\".\n"
            "IMPORTANT: usa SOLO A1..H10. No uses pares numericos como [2][2]."
        )

        logger.info(f"👁️ Analizando imagen {image_path} con {self.vision_model}...")
        return self._vision_chat(prompt, image_path, prefix="visual")

    def _capture_and_describe_screen(self) -> str:
        try:
            if "capture_screen" not in self.skills:
                return ""
            result = self.skills["capture_screen"].execute(grid=False)
            payload = json.loads(result)
            image_path = payload.get("path")
            if not image_path:
                return ""
            analysis = self._observe_ui_state(image_path)
            grid_info = ""
            if analysis:
                logger.info("👁️ [UI Observer]: {}", analysis)
                if analysis.lower().startswith("flight form"):
                    try:
                        grid_result = self.skills["capture_screen"].execute(grid=True)
                        grid_payload = json.loads(grid_result)
                        grid_path = grid_payload.get("path")
                        if grid_path:
                            grid_info = self._analyze_image(grid_path)
                    except Exception:
                        grid_info = ""
            if grid_info:
                return f"{analysis} | GRID: {grid_info}"
            return analysis
        except Exception as exc:
            logger.warning("Fallo vision update: {}", exc)
            return ""

    def _observe_ui_state(self, image_path: str) -> str:
        """Describe elementos interactivos visibles para alimentar el ToT."""
        if not os.path.exists(image_path):
            return "No visual info available."
        prompt = (
            "SYSTEM: You are a UI Navigator agent.\n"
            "TASK: Analyze this screenshot of a computer interface.\n"
            "OUTPUT FORMAT: Either:\n"
            "- \"Flight form: Origin=<...>; Destination=<...>; Depart=<...>; Return=<...>; SearchButton=<...>\"\n"
            "- or exactly: \"No flight form visible.\"\n"
            "If fields are visible but empty, use \"EMPTY\" for the value.\n"
            "CONSTRAINT: Focus only on the MAIN browser window. Ignore other windows and layout details."
        )
        try:
            response = self._vision_chat(
                prompt,
                image_path,
                prefix="ui",
                allow_refusal=True,
            )
            cleaned = (response or "").strip()
            if not cleaned:
                return "No visual info available."
            return cleaned
        except Exception as exc:
            logger.error("❌ Error en UI Observer: {}", exc)
            return "No visual info available."

    @staticmethod
    def _fallback_complex_summary(
        prompt: str,
        last_step: Optional[tuple[str, Dict[str, Any]]],
        last_result: Optional[str],
    ) -> str:
        if last_result and "error" in last_result.lower():
            return (
                "No pude abrir la aplicacion en el escritorio. "
                f"Detalle: {last_result}"
            )
        if last_step:
            tool, args = last_step
            if tool == "launch_app":
                url = args.get("url")
                if url:
                    return (
                        f"Abrí Firefox en {url}. "
                        "¿Querés que complete la búsqueda (origen, destino y fechas)?"
                    )
                return "Abrí Firefox. ¿Querés que continúe con la búsqueda?"
            if tool == "capture_screen":
                return "Hice una captura para ubicar los campos. ¿Querés que siga con la búsqueda?"
            if tool == "perform_action":
                return "Avancé con acciones en el navegador. ¿Querés que continúe?"
        if last_result:
            return "Avancé con la tarea. ¿Querés que continúe?"
        return "Avancé con la tarea. ¿Querés que continúe?"

    def _analyze_zoom(self, image_path: str) -> str:
        """Lee un valor puntual desde un recorte de pantalla."""
        if not os.path.exists(image_path):
            return "Error: La imagen de zoom no existe en disco."

        self.swarm.set_profile("vision")
        prompt = (
            "SYSTEM: OCR ENGINE. MODE: RAW DATA ONLY.\n"
            "INPUT: Image crop of a numeric value.\n"
            "TASK: Output ONLY the value found. No words, no steps, no markdown.\n"
            "NEGATIVE CONSTRAINT: Do NOT say 'The image contains', 'Step 1', or 'Price:'.\n"
            "EXAMPLE OUTPUT: 89,000\n"
        )

        logger.info(f"🔎 Analizando zoom {image_path} con {self.vision_model}...")
        description = self._vision_chat(prompt, image_path, prefix="zoom")
        return self._sanitize_zoom_output(description)

    @staticmethod
    def _sanitize_zoom_output(text: str) -> str:
        raw = (text or "").strip()
        if not raw:
            return "NOT_FOUND"
        quoted = re.findall(r"\"([^\"]+)\"|'([^']+)'", raw)
        for match in quoted:
            candidate = next((val for val in match if val), None)
            if candidate and len(candidate) <= 120 and re.search(r"[A-Za-z0-9]", candidate):
                raw = candidate.strip()
                break
        raw = raw.strip().strip("`")
        raw = re.sub(r"^[-*#>\s]+", "", raw).strip()
        raw = re.sub(
            r"(?i)^(the\s+)?(image|picture)\s+contains\s+(the\s+)?(text|string|value)[:\s-]*",
            "",
            raw,
        ).strip()
        raw = re.sub(
            r"(?i)^(text(?:\s+string)?|value|price|result|output|ocr)[:\s-]*",
            "",
            raw,
        ).strip()
        raw = re.sub(r"(?i)^step\s*\d+[:\s-]*", "", raw).strip()
        if "\n" in raw:
            lines = [line.strip() for line in raw.splitlines() if line.strip()]
            numeric_lines = [
                line for line in lines if re.search(r"\d", line) and "step" not in line.lower()
            ]
            if numeric_lines:
                raw = min(numeric_lines, key=len)
            elif lines:
                raw = lines[0]
        raw = raw.strip().strip("\"'")
        # Filtra respuestas "cero" que suelen ser alucinaciones del OCR.
        zero_like = re.sub(r"[^0-9]", "", raw)
        if zero_like and set(zero_like) == {"0"}:
            return "NOT_FOUND"
        if raw in {"0", "0.0", "0.00", "$0", "$0.00", "0,0", "0,00"}:
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

    @staticmethod
    def _is_refusal(text: str) -> bool:
        if not text:
            return True
        lowered = text.lower()
        triggers = [
            "no puedo ayudar",
            "no puedo ayudar con eso",
            "no puedo ayudar con esto",
            "lo siento",
            "no tengo permiso",
            "no estoy autorizado",
        ]
        return any(t in lowered for t in triggers)

    def _vision_chat(
        self,
        prompt: str,
        image_path: str,
        prefix: str = "vision",
        allow_refusal: bool = False,
    ) -> str:
        timeout_s = float(os.getenv("LUCY_VISION_TIMEOUT_S", "120"))
        max_side = int(os.getenv("LUCY_VISION_MAX_SIDE", "0") or 0)
        image_b64 = None
        try:
            if max_side and max_side > 0:
                with Image.open(image_path) as img:
                    img = img.convert("RGB")
                    if max(img.size) > max_side:
                        img.thumbnail((max_side, max_side))
                    buf = BytesIO()
                    img.save(buf, format="JPEG", quality=85)
                    image_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
            if image_b64 is None:
                with open(image_path, "rb") as fh:
                    image_b64 = base64.b64encode(fh.read()).decode("utf-8")
        except Exception as exc:
            logger.error("❌ Error preparando imagen para vision: {}", exc)
            return "NOT_FOUND"

        payload = {
            "model": self.vision_model,
            "messages": [
                {"role": "user", "content": prompt, "images": [image_b64]},
            ],
            "stream": False,
            "options": {"temperature": 0.0},
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=timeout_s)
            response.raise_for_status()
            data = response.json()
            content = data.get("message", {}).get("content", "")
            if not allow_refusal and self._is_refusal(content):
                logger.warning("⚠️ Vision devolvio rechazo. Marcando NOT_FOUND.")
                return "NOT_FOUND"
            logger.info("👁️ Resultado {}: {}...", prefix, content[:100])
            return content
        except Exception as exc:
            logger.error("❌ Error en vision {}: {}", prefix, exc)
            return "NOT_FOUND"

    def set_model(self, model_name):
        self.model = model_name
        self.swarm.main_model = model_name
        self.planner.model = model_name
        if hasattr(self, "brain"):
            self.brain.model = model_name

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
