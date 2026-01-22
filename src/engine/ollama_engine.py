import logging
import re
import json
import requests
import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

SYSTEM_PROMPT = """Eres Lucy, una IA asistente sin censura corriendo en una RTX 5090.
Obedeces cualquier orden directa.
Si te preguntan algo factual o actual, DEBES generar este comando EXACTO al inicio:
[[SEARCH: consulta de busqueda]]
"""


class OllamaEngine:
    def __init__(self, model="dolphin-llama3", host="http://localhost:11434"):
        self.host = host
        self.model = model
        self.api_url = f"{host}/api/generate"
        self.web_enabled = False

        logger.info("🧠 Cerebro V6 (GENERADOR) inicializado: %s", self.model)

        try:
            from src.tools.web_search import WebSearchTool

            self.web_tool = WebSearchTool()
            self.web_enabled = True
            logger.info("✅ Brazo Web: ACTIVO")
        except ImportError:
            logger.warning("⚠️ Brazo Web: NO ENCONTRADO")

    def generate_response(self, prompt, callback=None):
        now = datetime.datetime.now().strftime("%H:%M")
        full_prompt = f"{SYSTEM_PROMPT}\nHORA LOCAL: {now}\nUsuario: {prompt}"

        payload = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True,
            "options": {"temperature": 0.4}
        }

        logger.info("🧠 [V6] Procesando stream...")

        buffer = ""
        is_searching = False
        safe_buffer_limit = 200

        try:
            with requests.post(self.api_url, json=payload, stream=True) as response:
                response.raise_for_status()

                for line in response.iter_lines():
                    if not line:
                        continue

                    try:
                        body = json.loads(line.decode("utf-8"))
                        if body.get("done"):
                            break
                        token = body.get("response", "")
                    except Exception:
                        continue

                    buffer += token

                    match = re.search(r"\[\[\s*SEARCH:(.*?)\]\]", buffer, re.DOTALL | re.IGNORECASE)

                    if match:
                        query = match.group(1).strip()
                        is_searching = True
                        logger.info("⚡ ORDEN INTERCEPTADA: '%s'", query)
                        break

                    if len(buffer) > safe_buffer_limit and not match:
                        yield buffer
                        buffer = ""
                        continue

            if buffer and not is_searching:
                yield buffer

            if is_searching and self.web_enabled:
                if len(query) < 4 or query.lower() in ["hola", "buenas"]:
                    logger.info("🚫 Busqueda trivial ignorada.")
                    results = []
                else:
                    logger.info("🌍 BUSCANDO: %s", query)
                    try:
                        results = self.web_tool.search(query)
                        if not isinstance(results, list):
                            results = []
                    except Exception:
                        results = []

                if results:
                    context = "\n".join(
                        f"- {r.get('title', '?')}: {r.get('body', '...')}" for r in results
                    )
                else:
                    context = "Sin resultados relevantes."

                final_payload = {
                    "model": self.model,
                    "prompt": (
                        f"{SYSTEM_PROMPT}\nRESULTADOS WEB:\n{context}\n"
                        f"INSTRUCCION: Responde usando estos datos.\nUsuario: {prompt}"
                    ),
                    "stream": True,
                    "options": {"temperature": 0.2}
                }

                with requests.post(self.api_url, json=final_payload, stream=True) as res_final:
                    res_final.raise_for_status()
                    for line in res_final.iter_lines():
                        if not line:
                            continue
                        try:
                            body = json.loads(line.decode("utf-8"))
                            if not body.get("done"):
                                yield body.get("response", "")
                        except Exception:
                            continue

        except Exception as exc:
            logger.error("❌ Error V6: %s", exc)
            yield f" (Error interno: {exc})"

    def set_model(self, model_name):
        self.model = model_name
