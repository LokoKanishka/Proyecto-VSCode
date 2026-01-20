import os

# A. OBLIGAR A WHISPER A PENSAR EN ESPAÑOL
path_bridge = "src/engine/voice_bridge.py"
try:
    with open(path_bridge, "r") as f:
        content = f.read()

    # Inyectamos el 'initial_prompt' que elimina las traducciones al inglés
    if 'initial_prompt=' not in content:
        print("🔧 [Parche] Forzando español en el Oído...")
        content = content.replace(
            'condition_on_previous_text=False', 
            'condition_on_previous_text=False, initial_prompt="Esta es una conversación natural en español, argentina."'
        )
        with open(path_bridge, "w") as f:
            f.write(content)
    else:
        print("✅ [Parche] El Oído ya estaba parcheado.")
except FileNotFoundError:
    print("❌ No encuentro voice_bridge.py")

# B. REPROGRAMAR LA PERSONALIDAD (Para que deje de alucinar)
print("🧠 [Parche] Re-calibrando Personalidad...")
os.makedirs("src/engine", exist_ok=True)

code_ollama = '''import requests
import json

class OllamaEngine:
    def __init__(self, model="tinyllama"):
        self.model = model
        self.api_url = "http://localhost:11434/api/generate"
        self.system_prompt = "Eres Lucy, una asistente IA leal y sarcástica. Hablas SIEMPRE en español. Tus respuestas son cortas (máximo 2 frases)."

    def set_model(self, model_name):
        self.model = model_name

    def generate_response(self, prompt, chat_history=[]):
        full_prompt = f"{self.system_prompt}\nUser: {prompt}\nLucy:"
        
        data = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": True
        }

        try:
            with requests.post(self.api_url, json=data, stream=True) as response:
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            try:
                                json_response = json.loads(line)
                                if "response" in json_response:
                                    yield json_response["response"]
                            except: pass
        except Exception as e:
            yield f"Error: {e}"
'''

with open("src/engine/ollama_engine.py", "w") as f:
    f.write(code_ollama)

print("✅ PARCHE COMPLETADO.")
