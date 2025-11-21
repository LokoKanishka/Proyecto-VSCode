import logging
import subprocess
import json
from typing import Optional, Dict, Any
from lucy_voice.config import LucyConfig

class OllamaLLM:
    def __init__(self, config: LucyConfig):
        self.config = config
        self.log = logging.getLogger("OllamaLLM")

    def _extract_visible_answer(self, raw: str) -> str:
        marker = "...done thinking."
        if marker in raw:
            visible = raw.split(marker, 1)[1].strip()
            if visible:
                return visible

        for token in ["Respuesta:", "Answer:", "Final answer:", "Assistant:"]:
            if token in raw:
                tail = raw.split(token, 1)[1].strip()
                if tail:
                    return tail

        return raw

    def generate_response(self, prompt: str, tool_result: Optional[str] = None) -> str:
        self.log.info("Llamando a Ollama (modelo=%s)...", self.config.ollama_model)

        system_prompt = (
            "Sos Lucy, una asistente de voz local. "
            "Podés usar herramientas respondiendo SOLO con un JSON válido. "
            "Herramientas disponibles: "
            "abrir_aplicacion(nombre), abrir_url(url), tomar_captura(), escribir_texto(texto). "
            "Ejemplo: {\"tool\": \"abrir_aplicacion\", \"args\": [\"firefox\"]} "
            "Si no usás herramientas, respondé brevemente en español rioplatense."
        )

        if tool_result:
            full_prompt = (
                f"{system_prompt}\n"
                f"Resultado de la herramienta: {tool_result}\n"
                "Explicáselo al usuario brevemente."
            )
        else:
            full_prompt = (
                f"{system_prompt}\n"
                f"Usuario: {prompt}"
            )

        try:
            # TODO: Use requests or ollama python client if available for better control
            # For now keeping subprocess as per original implementation
            proc = subprocess.run(
                ["ollama", "run", self.config.ollama_model],
                input=full_prompt.encode("utf-8"),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            self.log.error("Error Ollama: %s", e)
            return "Tuve un problema con el modelo."

        raw = proc.stdout.decode("utf-8", errors="ignore").strip()
        self.log.debug("[Ollama raw] %r", raw)
        
        return self._extract_visible_answer(raw)

    def extract_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Intenta extraer un JSON de tool call del texto.
        """
        try:
            start = text.find("{")
            end = text.rfind("}")
            
            if start != -1 and end != -1:
                json_str = text[start:end+1]
                data = json.loads(json_str)
                
                if "tool" in data:
                    return data
        except Exception as e:
            self.log.warning(f"Error procesando posible tool: {e}")
            
        return None
