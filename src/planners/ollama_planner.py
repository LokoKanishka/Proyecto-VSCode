import json
import logging
import os
import re
from typing import Dict, Iterable, List, Optional

import requests

try:
    import yaml  # type: ignore
except Exception:
    yaml = None

from src.core.types import WorkerType
from src.planners.tree_of_thought import PlanStep

logger = logging.getLogger(__name__)

TARGET_ALIASES = {
    "search": WorkerType.SEARCH,
    "search_worker": WorkerType.SEARCH,
    "browser": WorkerType.BROWSER,
    "browser_worker": WorkerType.BROWSER,
    "vision": WorkerType.VISION,
    "vision_worker": WorkerType.VISION,
    "hands": WorkerType.HANDS,
    "hands_worker": WorkerType.HANDS,
    "shell": WorkerType.SHELL,
    "shell_worker": WorkerType.SHELL,
    "vscode": WorkerType.VSCODE,
    "vscode_worker": WorkerType.VSCODE,
    "git": WorkerType.GIT,
    "git_worker": WorkerType.GIT,
    "package": WorkerType.PACKAGE,
    "package_worker": WorkerType.PACKAGE,
    "code": WorkerType.CODE,
    "code_worker": WorkerType.CODE,
    "chat": WorkerType.CHAT,
    "chat_worker": WorkerType.CHAT,
    "memory": WorkerType.MEMORY,
    "memory_worker": WorkerType.MEMORY,
}


class OllamaPlanner:
    """Planificador basado en LLM (Ollama) que devuelve pasos estructurados."""

    def __init__(
        self,
        model: Optional[str] = None,
        host: Optional[str] = None,
        timeout_s: float = 20.0,
        max_steps: int = 4,
        config_path: str = "config.yaml",
    ):
        config = _load_config(config_path)
        self.host = host or os.getenv("LUCY_OLLAMA_HOST") or config.get("ollama_host") or "http://localhost:11434"
        self.model = model or os.getenv("LUCY_PLANNER_MODEL") or config.get("ollama_model") or "qwen2.5:32b"
        self.use_vllm = os.getenv("LUCY_USE_VLLM_PLANNER", "0").lower() in {"1", "true", "yes"}
        self.vllm_url = os.getenv("LUCY_VLLM_URL", "http://localhost:8000")
        self.vllm_model = os.getenv("LUCY_VLLM_MODEL", "qwen2.5-32b")
        self.timeout_s = timeout_s
        self.max_steps = max_steps

    def plan(
        self,
        prompt: str,
        context: Iterable[str] | None = None,
        max_depth: int = 2,
        beam_width: int = 3,
    ) -> List[PlanStep]:
        del max_depth, beam_width
        history = "\n".join(context or [])
        system_prompt = (
            "Sos el planificador de Lucy. Responde SOLO con JSON válido.\n"
            "Devuelve una LISTA de pasos. Cada paso debe tener:\n"
            "{\"action\": str, \"target\": str, \"args\": dict, \"rationale\": str}\n"
            "Targets válidos: search, browser, vision, hands, shell, vscode, git, package, code, chat, memory.\n"
            "Acciones esperadas por target:\n"
            "- search: action=search, args={query, max_results?, scrape?, snippets?, language?}\n"
            "- browser: action=open_url|run_actions|search_youtube|capture_state, args={url? steps? query? headless?}\n"
            "- vision: action=analyze_screen|analyze_image, args={prompt, advanced?}\n"
            "- hands: action=click_grid|type_text|press_hotkey|paste_text, args={grid_code? text? keys?}\n"
            "- shell: action=run_command, args={command, timeout?, allow_unsafe?}\n"
            "- vscode: action=open_file|insert_text|save_file|run_command, args={path? text? command?}\n"
            "- git: action=status|diff|log|add|commit|branch, args={args? cwd?}\n"
            "- package: action=list|show|install|uninstall, args={args?}\n"
            "- code: action=run_tests|lint, args={path?}\n"
            "- memory: action=summarize_history|retrieve_semantic|backup_memory, args={session_id? query? limit?}\n"
            "- chat: action=chat, args={text, history?}\n"
            "Patrones recomendados:\n"
            "- Si el usuario pega una URL y pide leer/resumir: primero browser:distill_url {url}.\n"
            "- Si hay interacción web compleja: browser:capture_state antes de decidir siguientes pasos.\n"
            "- Para extraer texto de páginas dinámicas: browser:capture_state o browser:distill_url.\n"
            f"Máximo {self.max_steps} pasos.\n"
            "Preferí el menor número de pasos posible.\n"
            "No agregues texto fuera del JSON."
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Contexto:\n{history}\n\nPedido:\n{prompt}"},
        ]
        raw = ""
        try:
            if self.use_vllm:
                raw = _chat_vllm(self.vllm_url, self.vllm_model, messages, timeout_s=self.timeout_s)
            else:
                response = _chat_http(self.host, self.model, messages, timeout_s=self.timeout_s)
                raw = response.get("message", {}).get("content", "")
        except Exception as exc:
            logger.warning("Planner LLM falló: %s", exc)
            return [
                PlanStep(
                    action="chat",
                    target=WorkerType.CHAT,
                    args={"text": prompt, "history": list(context or [])},
                    rationale="Fallback por error del planner.",
                )
            ]

        steps = _parse_steps(raw, self.max_steps)
        if not steps:
            return [
                PlanStep(
                    action="chat",
                    target=WorkerType.CHAT,
                    args={"text": prompt, "history": list(context or [])},
                    rationale="No pude parsear el plan; respondo conversacionalmente.",
                )
            ]
        return steps


def _parse_steps(raw: str, max_steps: int) -> List[PlanStep]:
    payload = _extract_json(raw)
    if payload is None:
        return []
    if isinstance(payload, dict):
        payload = payload.get("steps") or payload.get("plan") or []
    if not isinstance(payload, list):
        return []

    steps: List[PlanStep] = []
    for item in payload[:max_steps]:
        if not isinstance(item, dict):
            continue
        action = str(item.get("action") or "").strip()
        target_raw = str(item.get("target") or "").strip().lower()
        args = item.get("args") if isinstance(item.get("args"), dict) else {}
        rationale = item.get("rationale")
        target = TARGET_ALIASES.get(target_raw)
        if not target:
            try:
                target = WorkerType(target_raw)
            except Exception:
                target = WorkerType.CHAT
        if not action:
            action = _default_action_for_target(target)
            if action == "chat":
                target = WorkerType.CHAT
                args = {"text": args.get("text", "")}
        steps.append(PlanStep(action=action, target=target, args=args, rationale=rationale))
    return steps


def _default_action_for_target(target: WorkerType) -> str:
    defaults = {
        WorkerType.SEARCH: "search",
        WorkerType.BROWSER: "open_url",
        WorkerType.VISION: "analyze_screen",
        WorkerType.HANDS: "click_grid",
        WorkerType.SHELL: "run_command",
        WorkerType.VSCODE: "open_file",
        WorkerType.GIT: "status",
        WorkerType.PACKAGE: "list",
        WorkerType.CODE: "run_tests",
        WorkerType.MEMORY: "summarize_history",
        WorkerType.CHAT: "chat",
    }
    return defaults.get(target, "chat")


def _extract_json(text: str) -> Optional[object]:
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"(\[.*\])", text, flags=re.DOTALL)
    if not match:
        match = re.search(r"(\{.*\})", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _chat_http(
    host: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout_s: float = 20.0,
) -> Dict:
    payload = {"model": model, "messages": messages, "stream": False}
    response = requests.post(f"{host}/api/chat", json=payload, timeout=timeout_s)
    response.raise_for_status()
    return response.json()


def _chat_vllm(
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout_s: float = 20.0,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.2,
        "max_tokens": 512,
    }
    response = requests.post(f"{base_url}/v1/chat/completions", json=payload, timeout=timeout_s)
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def _load_config(path: str) -> Dict[str, str]:
    if not yaml:
        return {}
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}
