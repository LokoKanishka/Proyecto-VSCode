import requests
import json
import time

print("--- 🧠 DIAGNÓSTICO DE CEREBRO (OLLAMA) ---")

host = "http://127.0.0.1:11434"

# 1. Verificar si Ollama responde al ping básico
try:
    print(f"1. Probando conexión a {host} ...")
    r = requests.get(host, timeout=10)
    if r.status_code == 200:
        print("   ✅ Ollama está vivo y corriendo.")
    else:
        print(f"   ⚠️ Ollama respondió con código: {r.status_code}")
except Exception as e:
    print(f"   ❌ ERROR CRÍTICO: No se puede conectar a Ollama. {e}")
    exit()

# 2. Verificar si el modelo responde (SIN STREAMING)
model = "phi3" 
print(f"\n2. Intentando generar texto con '{model}'...")

url = f"{host}/api/chat"
payload = {
    "model": model,
    "messages": [{"role": "user", "content": "Responde solo la palabra FUNCIONA."}],
    "stream": False 
}

start = time.time()
try:
    print("   📤 Enviando solicitud...")
    r = requests.post(url, json=payload, timeout=60)
    
    if r.status_code == 200:
        response = r.json()
        content = response.get("message", {}).get("content", "VACÍO")
        print(f"   ✅ RESPUESTA RECIBIDA en {time.time() - start:.2f}s")
        print(f"   🗣️ Dice: {content}")
    else:
        print(f"   ❌ Error del modelo: {r.text}")

except Exception as e:
    print(f"   ❌ Error enviando prompt: {e}")

print("\n--- FIN DEL DIAGNÓSTICO ---")
