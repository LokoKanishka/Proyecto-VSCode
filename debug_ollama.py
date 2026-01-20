import ollama
import sys

print("--- Ollama Debug ---")
try:
    print("Attempting ollama.list()...")
    models = ollama.list()
    print(f"Result: {models}")
    
    if 'models' in models:
        names = [m['name'] for m in models['models']]
        print(f"Model Names: {names}")
    else:
        print("Structure unexpected:", models)

except Exception as e:
    print(f"CRITICAL ERROR: {e}")
    import traceback
    traceback.print_exc()

print("--------------------")
