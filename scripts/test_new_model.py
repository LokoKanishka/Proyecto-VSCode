import ollama
import time

def test_inference(model_name="qwen2.5:32b"):
    print(f"Testing model: {model_name}")
    prompt = "Escribe un poema breve sobre la inteligencia artificial y el hardware potente, en español rioplatense."
    
    start_time = time.time()
    response = ollama.generate(model=model_name, prompt=prompt, stream=False)
    end_time = time.time()
    
    duration = end_time - start_time
    eval_count = response.get('eval_count', 0)
    tokens_per_sec = eval_count / duration if duration > 0 else 0
    
    print("-" * 30)
    print(f"Respuesta:\n{response['response']}")
    print("-" * 30)
    print(f"Tiempo total: {duration:.2f}s")
    print(f"Tokens generados: {eval_count}")
    print(f"Velocidad: {tokens_per_sec:.2f} tokens/s")
    
    if tokens_per_sec > 25:
        print("RESULTADO: 🚀 EXCELENTE (Corre en VRAM)")
    elif tokens_per_sec > 5:
        print("RESULTADO: 🟢 OK (Probable balance VRAM/RAM)")
    else:
        print("RESULTADO: 🔴 LENTO (Probable RAM offloading)")

if __name__ == "__main__":
    test_inference()
