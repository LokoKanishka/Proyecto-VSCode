import requests
import json

class OllamaEngine:
    def __init__(self, model="qwen2:1.5b", host="http://127.0.0.1:11434"):
        self.model = model
        self.host = host
        print(f"🧠 [Engine] Cerebro listo ({model}).")

    def set_model(self, model_name):
        self.model = model_name
        print(f"🔄 [Engine] Modelo cambiado a: {model_name}")

    def load_model(self, model_name):
        self.model = model_name
        print(f"🔄 [Engine] Modelo cargado: {model_name}")

    def list_models(self):
        try:
            url = f"{self.host}/api/tags"
            response = requests.get(url, timeout=5)
            data = response.json()
            return [m["name"].split(":")[0] for m in data.get("models", [])]
        except Exception as e:
            print(f"❌ [Ollama] Error listing models: {e}")
            return []

    def generate_response(self, chat_history):
        """
        Generates response in STREAMING mode.
        """
        url = f"{self.host}/api/chat"
        
        # INSTRUCCIÓN DE PERSONALIDAD (System Prompt)
        system_msg = {
            "role": "system", 
            "content": "Eres Lucy, una asistente IA Cyberpunk. Respondes SIEMPRE en español. Tus respuestas son breves, útiles y con actitud. No traduzcas al inglés."
        }

        # Inyectar o reemplazar el system prompt
        if not chat_history or chat_history[0]["role"] != "system":
            chat_history.insert(0, system_msg)
        else:
            chat_history[0] = system_msg

        payload = {
            "model": self.model,
            "messages": chat_history,
            "stream": True, 
            "options": {
                "num_predict": 100,
                "temperature": 0.7,
                "repeat_penalty": 1.2,
                "stop": ["User:", "\n\n", "Assistant:"]
            }
        }

        try:
            print(f"🧠 [Engine] Pensando ({self.model})...")
            r = requests.post(url, json=payload, stream=True, timeout=60)
            r.raise_for_status()
            
            for line in r.iter_lines():
                if line:
                    body = json.loads(line)
                    if "message" in body and "content" in body["message"]:
                        chunk = body["message"]["content"]
                        yield chunk
                    if body.get("done", False):
                        break
                        
        except Exception as e:
            print(f"❌ [Engine] Error: {e}")
            yield f"[Error: {e}]"
