import json
import re
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests
try:
    from loguru import logger
except Exception:  # pragma: no cover - fallback for minimal envs
    import logging

    class _LoggerShim:
        def __init__(self, base_logger: logging.Logger):
            self._logger = base_logger

        def _log(self, level: int, message: str, *args: Any) -> None:
            if args:
                message = message.replace("{}", "%s")
                self._logger.log(level, message, *args)
            else:
                self._logger.log(level, message)

        def debug(self, message: str, *args: Any) -> None:
            self._log(logging.DEBUG, message, *args)

        def info(self, message: str, *args: Any) -> None:
            self._log(logging.INFO, message, *args)

        def warning(self, message: str, *args: Any) -> None:
            self._log(logging.WARNING, message, *args)

        def error(self, message: str, *args: Any) -> None:
            self._log(logging.ERROR, message, *args)

    logger = _LoggerShim(logging.getLogger(__name__))
try:
    import ollama
except Exception:  # pragma: no cover - optional dependency
    ollama = None

from src.engine.swarm_manager import SwarmManager


def _chat_http(
    host: str,
    model: str,
    messages: List[Dict[str, Any]],
    options: Optional[Dict[str, Any]] = None,
    timeout_s: float = 20.0,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": options or {},
    }
    response = requests.post(f"{host}/api/chat", json=payload, timeout=timeout_s)
    response.raise_for_status()
    return response.json()


class Planner:
    def __init__(
        self,
        swarm: SwarmManager,
        model: str,
        host: str,
        timeout_s: float = 20.0,
    ):
        self.swarm = swarm
        self.model = model
        self.host = host
        self.timeout_s = timeout_s
        try:
            if ollama is None:
                raise RuntimeError("ollama lib not available")
            self.client = ollama.Client(host=host)
        except Exception:
            self.client = None

    def plan(self, user_request: str, max_steps: int = 8) -> List[Dict[str, Any]]:
        """Genera un plan JSON de pasos usando las tools existentes."""
        self.swarm.set_profile("general")
        system_prompt = (
            "SOS LUCY. Tu tarea es PLANIFICAR, no ejecutar.\n"
            "Devuelve SOLO un JSON valido (lista de pasos).\n"
            "Cada paso debe tener: {\"tool\": \"...\", \"args\": {...}}.\n"
            "Herramientas disponibles:\n"
            "- perform_action: {action: \"hotkey\"|\"type\"|\"scroll\"|\"move_and_click\"|\"click_grid\", "
            "text?: str, keys?: [str], clicks?: int, grid?: str, x?: int, y?: int}\n"
            "- capture_screen: {grid?: bool, overlay_grid?: bool}\n"
            "- remember: {text: \"resumen breve\"}\n"
            "- launch_app: {app_name: \"firefox\", url?: \"https://...\"}\n"
            "- capture_region: {grid: \"C4\", padding?: 60}\n"
            "Reglas:\n"
            f"- Maximo {max_steps} pasos.\n"
            "- Regla #0 (cold start): NO asumas apps abiertas. Si la tarea es web, ABRI Firefox primero.\n"
            "- Para abrir Firefox: launch_app(app_name='firefox', url='https://...') -> capture_screen.\n"
            "- URLs directas: si el usuario pide un tema en un sitio conocido, abri la URL final.\n"
            "  Ejemplos:\n"
            "  - Wikipedia: https://es.wikipedia.org/wiki/Tema\n"
            "  - Google: https://www.google.com/search?q=consulta\n"
            "  - GitHub: https://github.com/ORG/REPO (si aplica)\n"
            "- Regla de oro: NUNCA tipear sin asegurar foco.\n"
            "- Para escribir en un input: capture_screen(grid=true) -> click_grid -> type.\n"
            "- NO uses atajos tipo '/' para enfocar busquedas.\n"
            "- Usa SOLO Firefox (no Chrome/Edge).\n"
            "- Si necesitas hacer click, USA un grid A1..H10 real. No inventes etiquetas.\n"
            "- Si el usuario pide un valor exacto, luego de ubicar la celda usa capture_region para confirmarlo.\n"
            "- Si ya usaste launch_app con URL, NO uses ctrl+l ni reescribas la direccion.\n"
            "- Usa remember para guardar datos clave que luego se usaran en la respuesta.\n"
            "- Si necesitas leer, usa capture_screen antes.\n"
            "- Para navegar dentro del browser: perform_action hotkey ctrl+l, luego type la URL, luego hotkey enter.\n"
            "- No incluyas explicaciones ni texto fuera del JSON.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request},
        ]

        try:
            if self.client:
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.2},
                    stream=False,
                )
            elif ollama is not None:
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.2},
                    stream=False,
                )
            else:
                response = _chat_http(
                    self.host,
                    self.model,
                    messages,
                    options={"temperature": 0.2},
                    timeout_s=self.timeout_s,
                )
            content = response.get("message", {}).get("content", "")
            plan = self._parse_plan(content)
            if not plan:
                logger.warning("Planner devolvio plan vacio o invalido.")
            return plan[:max_steps]
        except Exception as exc:
            logger.warning("Planner fallo generando plan: {}", exc)
            return []

    @staticmethod
    def _parse_plan(raw: str) -> List[Dict[str, Any]]:
        text = (raw or "").strip()
        if not text:
            return []
        # Intento directo
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return Planner._sanitize_steps(data)
        except Exception:
            pass
        # Extraer bloque JSON
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                if isinstance(data, list):
                    return Planner._sanitize_steps(data)
            except Exception:
                pass
        return []

    @staticmethod
    def _sanitize_steps(steps: List[Any]) -> List[Dict[str, Any]]:
        clean: List[Dict[str, Any]] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            tool = step.get("tool")
            args = step.get("args") or {}
            if not isinstance(tool, str) or not isinstance(args, dict):
                continue
            clean.append({"tool": tool, "args": args})
        has_direct_url = any(
            step["tool"] == "launch_app" and step["args"].get("url") for step in clean
        )
        if not has_direct_url:
            return clean

        filtered: List[Dict[str, Any]] = []
        for step in clean:
            if step["tool"] != "perform_action":
                filtered.append(step)
                continue

            args = step.get("args") or {}
            action = str(args.get("action") or args.get("action_type") or args.get("command") or "").lower()
            text = str(args.get("text") or "")
            keys = args.get("keys")

            if action == "hotkey":
                if isinstance(keys, list):
                    key_list = [str(k).lower() for k in keys]
                else:
                    key_list = [k for k in text.lower().replace("+", " ").split() if k]
                if "ctrl" in key_list and ("l" in key_list or "f6" in key_list):
                    continue

            if action == "type":
                lowered = text.strip().lower()
                if lowered.startswith("http") or lowered.startswith("www.") or lowered.startswith("/#"):
                    continue

            filtered.append(step)

        return filtered


@dataclass
class ThoughtNode:
    id: str
    parent: Optional["ThoughtNode"]
    plan_step: Dict[str, Any]
    state_snapshot: str
    score: float = 0.0
    status: str = "unvisited"
    depth: int = 0
    children: List["ThoughtNode"] = field(default_factory=list)


class ThoughtEngine:
    def __init__(
        self,
        swarm: SwarmManager,
        model: str,
        host: str,
        timeout_s: float = 20.0,
        max_depth: int = 3,
        max_nodes: int = 10,
        prune_threshold: float = 0.3,
    ):
        self.swarm = swarm
        self.model = model
        self.host = host
        self.timeout_s = timeout_s
        self.max_depth = max_depth
        self.max_nodes = max_nodes
        self.prune_threshold = prune_threshold
        try:
            if ollama is None:
                raise RuntimeError("ollama lib not available")
            self.client = ollama.Client(host=host)
        except Exception:
            self.client = None

    def propose_next_steps(self, node: ThoughtNode, k: int = 3) -> List[ThoughtNode]:
        """Genera k candidatos de siguiente paso a partir del estado actual."""
        self.swarm.set_profile("general")
        system_prompt = (
            f"GOAL STATE: {node.state_snapshot}\n"
            f"TASK: Generate exactly {k} distinct, valid next steps.\n"
            "CONTEXT: You are a desktop automation agent operating a specific UI.\n"
            "STRICT CONSTRAINT: Propose ONLY steps that directly advance the current GOAL STATE.\n"
            "NEGATIVE CONSTRAINTS: Do NOT propose medical advice, coins/crypto, math puzzles, "
            "general knowledge, or hypothetical tasks.\n"
            "If unsure, propose capture_screen(grid=true) to get UI evidence.\n"
            "OUTPUT FORMAT: A single valid JSON list of objects. "
            "Do NOT use markdown code blocks. Do NOT write explanations.\n"
            "JSON STRUCTURE MUST BE EXACTLY LIKE THIS:\n"
            "[\n"
            "  {\"tool\": \"tool_name\", \"args\": {\"arg1\": \"value1\"}},\n"
            "  {\"tool\": \"tool_name\", \"args\": {\"arg1\": \"value1\"}}\n"
            "]\n"
            "CRITICAL: Ensure every open brace '{' has a matching closing brace '}'. "
            "Check your syntax.\n"
            "TOOLS:\n"
            "- perform_action: {action: \"hotkey\"|\"type\"|\"scroll\"|\"move_and_click\"|\"click_grid\", "
            "text?: str, keys?: [str], clicks?: int, grid?: str, x?: int, y?: int}\n"
            "- capture_screen: {grid?: bool, overlay_grid?: bool}\n"
            "- remember: {text: \"resumen breve\"}\n"
            "- launch_app: {app_name: \"firefox\", url?: \"https://...\"}\n"
            "- capture_region: {grid: \"C4\", padding?: 60}\n"
            "RULES:\n"
            "- Regla #0 (cold start): NO asumas apps abiertas. Si la tarea es web y NO hay evidencia de navegador "
            "abierto o un [SCREEN UPDATE], ABRI Firefox primero.\n"
            "- Si el estado indica 'app lanzada (firefox)' o ya hay [SCREEN UPDATE], NO vuelvas a launch_app.\n"
            "- Para abrir Firefox: launch_app(app_name='firefox', url='https://...') -> capture_screen.\n"
            "- NEVER guess deep URLs (e.g. https://skyscanner.com/flights/...). Always start at the Homepage "
            "(skyscanner.com) and use UI interaction to search.\n"
            "- NO inventes ciudades/aeropuertos. Usa solo destinos/origenes mencionados por el usuario. "
            "Si falta informacion, pedila o espera una captura con los campos.\n"
            "- If you see input fields (e.g. Origin/Destination), use perform_action('type', ...) to fill them. "
            "If you see a Search button, click it.\n"
            "- If you need to type into a specific field and don't have focus, do: capture_screen(grid=true) "
            "then perform_action(click_grid, grid=\"...\") to focus the field, then type.\n"
            "- Si necesitas hacer click, USA un grid A1..H10 real. No inventes etiquetas.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
        ]

        content = ""
        try:
            if self.client:
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.4},
                    stream=False,
                )
            elif ollama is not None:
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.4},
                    stream=False,
                )
            else:
                response = _chat_http(
                    self.host,
                    self.model,
                    messages,
                    options={"temperature": 0.4},
                    timeout_s=self.timeout_s,
                )
            content = response.get("message", {}).get("content", "")
            steps = self._parse_candidates(self._extract_json_block(content))
        except Exception as exc:
            logger.warning("ThoughtEngine fallo proponiendo pasos: {}", exc)
            steps = []
        if not steps and content:
            # Intento de reparación: pedir formato JSON estricto usando la salida cruda
            repair_system_prompt = (
                f"Convert the user content into EXACTLY {k} JSON objects in a JSON list.\n"
                "Output MUST be valid JSON only (no markdown). If impossible, output [].\n"
                "Schema: [{\"tool\": \"tool_name\", \"args\": {\"arg\": \"value\"}}]\n"
                "Allowed tools: perform_action, capture_screen, remember, launch_app, capture_region.\n"
            )
            try:
                repair_messages = [
                    {"role": "system", "content": repair_system_prompt},
                    {"role": "user", "content": content},
                ]
                if self.client:
                    repair = self.client.chat(
                        model=self.model,
                        messages=repair_messages,
                        options={"temperature": 0.0},
                        stream=False,
                    )
                elif ollama is not None:
                    repair = ollama.chat(
                        model=self.model,
                        messages=repair_messages,
                        options={"temperature": 0.0},
                        stream=False,
                    )
                else:
                    repair = _chat_http(
                        self.host,
                        self.model,
                        repair_messages,
                        options={"temperature": 0.0},
                        timeout_s=self.timeout_s,
                    )
                repair_content = repair.get("message", {}).get("content", "")
                steps = self._parse_candidates(self._extract_json_block(repair_content))
            except Exception as exc:
                logger.warning("ThoughtEngine fallo reparando candidatos: {}", exc)
            if not steps:
                logger.warning(
                    "ThoughtEngine no pudo parsear candidatos. Respuesta cruda: {}",
                    content[:400],
                )

        children: List[ThoughtNode] = []
        for step in steps:
            if not self._validate_candidate(step, node.state_snapshot):
                continue
            if self._is_repeat_launch(node, step):
                continue
            child = ThoughtNode(
                id=str(uuid.uuid4()),
                parent=node,
                plan_step=step,
                state_snapshot=node.state_snapshot,
                depth=node.depth + 1,
            )
            children.append(child)
            if len(children) >= k:
                break

        node.children.extend(children)
        return children

    @staticmethod
    def _is_repeat_launch(node: ThoughtNode, step: Dict[str, Any], max_hops: int = 2) -> bool:
        tool = str(step.get("tool") or "").lower()
        if tool != "launch_app":
            return False
        args = step.get("args") or {}
        if not isinstance(args, dict):
            return False
        target_app = str(args.get("app_name") or "").lower()
        target_url = str(args.get("url") or "").strip()
        snapshot = (node.state_snapshot or "").lower()
        if target_app and (
            f"app lanzada ({target_app})" in snapshot
            or f"app ya estaba abierta ({target_app})" in snapshot
        ):
            return True
        cur = node
        hops = 0
        while cur and hops < max_hops:
            plan_step = cur.plan_step or {}
            if isinstance(plan_step, dict) and str(plan_step.get("tool") or "").lower() == "launch_app":
                prev_args = plan_step.get("args") or {}
                if isinstance(prev_args, dict):
                    app = str(prev_args.get("app_name") or "").lower()
                    url = str(prev_args.get("url") or "").strip()
                    if app and app == target_app and (not target_url or url == target_url):
                        return True
            cur = cur.parent
            hops += 1
        return False

    def evaluate_node(self, node: ThoughtNode) -> ThoughtNode:
        """Puntúa un nodo con el LLM para decidir viabilidad."""
        self.swarm.set_profile("general")
        system_prompt = (
            "SOS LUCY. Evaluá la acción propuesta.\n"
            "Devuelve SOLO JSON valido: {\"score\": 0.0-1.0, \"feedback\": \"...\"}.\n"
            "Criterios: relevancia con el objetivo, seguridad y factibilidad.\n"
            "SE LAXO: si la acción mueve la tarea hacia adelante aunque sea un poco, "
            "usa un score > 0.6.\n"
        )
        payload = {
            "estado": node.state_snapshot,
            "accion": node.plan_step,
        }
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
        ]

        try:
            if self.client:
                response = self.client.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.2},
                    stream=False,
                )
            elif ollama is not None:
                response = ollama.chat(
                    model=self.model,
                    messages=messages,
                    options={"temperature": 0.2},
                    stream=False,
                )
            else:
                response = _chat_http(
                    self.host,
                    self.model,
                    messages,
                    options={"temperature": 0.2},
                    timeout_s=self.timeout_s,
                )
            content = response.get("message", {}).get("content", "")
            score, feedback = self._parse_score(content)
            node.score = score
            node.status = "visited"
            if feedback:
                logger.debug("Feedback evaluación nodo {}: {}", node.id, feedback)
        except Exception as exc:
            logger.warning("ThoughtEngine fallo evaluando nodo: {}", exc)
            node.score = 0.0
            node.status = "visited"
        return node

    def search_dfs(self, root_node: ThoughtNode) -> Optional[ThoughtNode]:
        """DFS con profundidad fija y limite de nodos."""
        best_node: Optional[ThoughtNode] = None
        best_score = -1.0
        visited_nodes = 0
        stack: List[ThoughtNode] = [root_node]

        while stack and visited_nodes < self.max_nodes:
            node = stack.pop()
            if node.status != "unvisited":
                continue

            if node.parent is None and not node.plan_step:
                node.score = 1.0
                node.status = "visited"
                visited_nodes += 1
            else:
                self.evaluate_node(node)
                visited_nodes += 1

            if node is not root_node and node.plan_step and node.score > best_score:
                best_node = node
                best_score = node.score

            if node.score < self.prune_threshold:
                node.status = "pruned"
                continue

            if node.depth >= self.max_depth:
                continue

            children = self.propose_next_steps(node)
            for child in reversed(children):
                stack.append(child)

        if best_node and best_node.plan_step:
            logger.info(
                "🏆 [ThoughtEngine] Best step selected: {} (Score: {:.2f})",
                best_node.plan_step,
                best_node.score,
            )
        return best_node

    @staticmethod
    def _extract_json_block(raw: str) -> str:
        text = (raw or "").strip()
        if "```" not in text:
            return text
        # Prefer fenced json block if present
        matches = re.findall(r"```(?:json)?\\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
        if matches:
            return matches[0].strip()
        return text.replace("```", "").strip()

    @staticmethod
    def _text_looks_like_url(text: str) -> bool:
        lowered = text.lower().strip()
        if "://" in lowered or lowered.startswith("www."):
            return True
        if "." in lowered and " " not in lowered:
            return True
        return False

    @staticmethod
    def _validate_candidate(step: Dict[str, Any], state_snapshot: str = "") -> bool:
        tool = str(step.get("tool") or "")
        args = step.get("args") or {}
        if not isinstance(args, dict):
            return False
        action = str(args.get("action") or "").lower()
        grid = args.get("grid") or args.get("grid_id") or args.get("grid_code")
        if grid and isinstance(grid, str):
            grid_clean = grid.strip().upper()
            if not re.match(r"^[A-H](10|[1-9])$", grid_clean):
                return False
        if tool == "type" or (tool == "perform_action" and action == "type"):
            text = str(args.get("text") or "")
            keys = args.get("keys") or []
            keys_list: list[str] = []
            if isinstance(keys, str):
                keys_list = [k for k in keys.replace("+", " ").split() if k]
            elif isinstance(keys, (list, tuple)):
                keys_list = [str(k) for k in keys if k]
            if len(text) > 50 or "\n" in text or "```" in text:
                return False
            if text and not ThoughtEngine._text_looks_like_url(text):
                # Require an explicit focus action before typing into fields.
                snapshot = (state_snapshot or "").lower()
                keys_lower = [k.lower().strip() for k in keys_list if k]
                only_nav_keys = bool(keys_lower) and all(k in {"enter", "return", "tab"} for k in keys_lower)
                has_modifier = any(k in {"ctrl", "alt", "shift", "control"} for k in keys_lower)
                if (not keys_lower or only_nav_keys) and not has_modifier:
                    if "[focus ok]" not in snapshot and "click ejecutado" not in snapshot:
                        return False
        # capture_screen acepta overlay_grid (default True). No exijamos "grid" explícito
        # porque DesktopVisionSkill ya dibuja la grilla por defecto.
        return True

    @staticmethod
    def _parse_candidates(raw: str) -> List[Dict[str, Any]]:
        text = (raw or "").strip()
        if not text:
            return []
        try:
            data = json.loads(text)
            if isinstance(data, list):
                return Planner._sanitize_steps(data)
        except Exception:
            pass
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                data = json.loads(text[start : end + 1])
                if isinstance(data, list):
                    return Planner._sanitize_steps(data)
            except Exception:
                return []
        decoder = json.JSONDecoder()
        collected: List[Dict[str, Any]] = []
        for idx in range(len(text)):
            if text[idx] not in "[{":
                continue
            try:
                obj, _ = decoder.raw_decode(text[idx:])
            except Exception:
                continue
            if isinstance(obj, list):
                return Planner._sanitize_steps(obj)
            if isinstance(obj, dict) and "tool" in obj:
                collected.append(obj)
        if collected:
            return Planner._sanitize_steps(collected)
        return []

    @staticmethod
    def _parse_score(raw: str) -> tuple[float, str]:
        text = (raw or "").strip()
        if not text:
            return 0.0, ""
        try:
            data = json.loads(text)
            score = float(data.get("score", 0.0))
            feedback = str(data.get("feedback") or "")
            return max(0.0, min(1.0, score)), feedback.strip()
        except Exception:
            pass
        number = None
        try:
            number = float(text)
        except Exception:
            number = None
        if number is not None:
            return max(0.0, min(1.0, number)), ""
        return 0.0, ""
