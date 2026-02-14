import aiohttp
import asyncio
import time
import sys

# CONFIGURACIÓN
MODEL = "qwen2.5:32b"
URL = "http://localhost:11434/api/generate"

# PROMPTS DE ALTA ENTROPÍA
PROMPTS = [
    "Diseña una arquitectura de microservicios para un sistema bancario resistente a fallos bizantinos.",
    "Explica la diferencia entre 'Ser' y 'Ente' en Heidegger usando analogías de programación.",
    "Calcula y explica la complejidad temporal de un algoritmo de búsqueda A* en un grafo infinito.",
    "Escribe un poema recursivo donde el último verso sea el inicio del primero."
]

async def query(session, prompt, i):
    start = time.time()
    print(f"🔹 [Agente {i}] Pensando...")
    try:
        async with session.post(URL, json={"model": MODEL, "prompt": prompt, "stream": False}) as resp:
            if resp.status != 200: return print(f"❌ Error {resp.status}")
            res = await resp.json()
            dur = time.time() - start
            tps = res.get('eval_count', 0) / dur
            print(f"✅ [Agente {i}] {res.get('eval_count',0)} tokens en {dur:.2f}s | Velocidad: {tps:.2f} t/s")
            return tps
    except Exception as e:
        print(f"💀 Error: {e}")
        return 0

async def main():
    print(f"🔥 INICIANDO ESTRÉS EN RTX 5090 ({MODEL})")
    async with aiohttp.ClientSession() as session:
        tasks = [query(session, p, i+1) for i, p in enumerate(PROMPTS)]
        results = await asyncio.gather(*tasks)
    
    valid_results = [r for r in results if r]
    if valid_results:
        avg = sum(valid_results)/len(valid_results)
        print(f"\n📊 PROMEDIO FINAL: {avg:.2f} tokens/seg")
        if avg > 30: print("🚀 ESTADO: SOBERANO (La 5090 vuela)")
        elif avg > 10: print("⚠️ ESTADO: FUNCIONAL PERO LENTO")
        else: print("❌ ESTADO: CRÍTICO")
    else:
        print("\n❌ FALLO TOTAL: Ningún agente recibió respuesta.")

if __name__ == "__main__":
    try: asyncio.run(main())
    except ImportError: print("Instala aiohttp: pip install aiohttp")
