import requests
import json

class OllamaEngine:
    def __init__(self, model="qwen2:1.5b"):
        # FORZAMOS QWEN2 AUNQUE LA INTERFAZ DIGA OTRA COSA
        self.model = "qwen2:1.5b" 
        self.api_url = "http://localhost:11434/api/generate"
        
        # PERSONALIDAD: ARGENTINA Y CULTA
        self.system_prompt = (
            "Eres Lucy, una asistente IA experta y con actitud. "
            "Hablas SIEMPRE en español nativo. "
            "Nunca respondas en inglés (nada de 'Certainly' o 'Here is'). "
            "Si te preguntan por cultura (como Martín Fierro), cita el texto original exacto, no inventes. "
            "Sé breve y directa."
        )

    def set_model(self, model_name):
        # Ignoramos el cambio de modelo de la interfaz para proteger al usuario
        print(f"🔒 [Engine] Manteniendo modelo blindado: {self.model}")

    def generate_response(self, prompt, chat_history=[]):
        full_prompt = f"{self.system_prompt}\nUsuario: {prompt}\nLucy:"
        
        data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True,
            "options": {
                "temperature": 0.7, # Creatividad controlada
                "num_predict": 150  # Respuestas no muy largas
            }
        }

        try:
            with requests.post(self.api_url, json=data, stream=True) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            json_response = json.loads(line)
                            if "response" in json_response:
                                yield json_response["response"]
        except Exception as e:
            yield f"Error cerebral: {e}"
