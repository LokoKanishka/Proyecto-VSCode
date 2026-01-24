import json
from typing import Any, Dict, List, Optional

from loguru import logger
import ollama

from src.engine.swarm_manager import SwarmManager


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
            "Reglas:\n"
            f"- Maximo {max_steps} pasos.\n"
            "- Regla de oro: NUNCA tipear sin asegurar foco.\n"
            "- Para escribir en un input: capture_screen(grid=true) -> click_grid -> type.\n"
            "- NO uses atajos tipo '/' para enfocar busquedas.\n"
            "- Usa remember para guardar datos clave que luego se usaran en la respuesta.\n"
            "- Si necesitas leer, usa capture_screen antes.\n"
            "- Para navegar: perform_action hotkey ctrl+l, luego type la URL, luego hotkey enter.\n"
            "- No incluyas explicaciones ni texto fuera del JSON.\n"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_request},
        ]

        client = self.client or ollama
        try:
            response = client.chat(
                model=self.model,
                messages=messages,
                options={"temperature": 0.2},
                stream=False,
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
                return []
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
        return clean
