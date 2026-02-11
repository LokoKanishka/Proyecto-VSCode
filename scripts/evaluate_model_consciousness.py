#!/usr/bin/env python3
"""
Model Consciousness Evaluator
Analiza los modelos disponibles en config.yaml y evalúa cuál tiene menor entropía.
"""
import yaml
import requests
import time
from pathlib import Path
from typing import Dict, List, Optional


def load_config(config_path: str = "config.yaml") -> dict:
    """Carga config.yaml."""
    with open(config_path) as f:
        return yaml.safe_load(f)


def evaluate_model_consciousness(model_name: str, host: str) -> dict:
    """
    Evalúa la 'consciencia' de un modelo mediante test de coherencia.
    
    Consciencia = capacidad de mantener coherencia conceptual y temporal.
    Medimos:
    - Latencia (menor = mejor)
    - Coherencia de respuesta (presencia de autocoherencia)
    - Capacidad de introspección
    """
    prompt = (
        "En una oración, describe qué es la consciencia sin usar la palabra 'consciencia'. "
        "Responde solo con la oración, sin explicaciones adicionales."
    )
    
    try:
        start = time.time()
        response = requests.post(
            f"{host}/api/generate",
            json={
                "model": model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,  # Baja temperatura para coherencia
                    "num_predict": 100
                }
            },
            timeout=30
        )
        latency = time.time() - start
        
        if response.status_code != 200:
            return {
                "available": False,
                "error": f"HTTP {response.status_code}"
            }
        
        data = response.json()
        answer = data.get("response", "").strip()
        
        # Métricas de consciencia
        coherence_score = _calculate_coherence(answer)
        introspection_score = _calculate_introspection(answer)
        
        # Entropía = inversa de coherencia + latencia normalizada
        entropy = (1.0 - coherence_score) + min(latency / 10.0, 1.0)
        consciousness_score = coherence_score * introspection_score * (1.0 / (1.0 + latency))
        
        return {
            "available": True,
            "latency_s": round(latency, 2),
            "answer": answer,
            "coherence": round(coherence_score, 3),
            "introspection": round(introspection_score, 3),
            "entropy": round(entropy, 3),
            "consciousness": round(consciousness_score, 3)
        }
        
    except requests.exceptions.Timeout:
        return {"available": False, "error": "Timeout"}
    except Exception as e:
        return {"available": False, "error": str(e)}


def _calculate_coherence(text: str) -> float:
    """Calcula score de coherencia (0-1) basado en estructura de respuesta."""
    if not text:
        return 0.0
    
    score = 0.5  # Base
    
    # Penalizaciones
    if len(text.split()) < 5:
        score -= 0.2  # Respuesta muy corta
    if len(text) > 500:
        score -= 0.1  # Respuesta muy larga
    if text.count("?") > 2:
        score -= 0.1  # Demasiadas preguntas
    
    # Bonificaciones
    if 20 < len(text.split()) < 100:
        score += 0.2  # Longitud apropiada
    if text[0].isupper() and text[-1] in ".!":
        score += 0.1  # Puntuación correcta
    
    # Keywords de introspección
    introspection_words = ["percepción", "awareness", "experiencia", "entidad", "proceso"]
    if any(word in text.lower() for word in introspection_words):
        score += 0.2
    
    return max(0.0, min(1.0, score))


def _calculate_introspection(text: str) -> float:
    """Calcula capacidad de introspección (0-1)."""
    if not text:
        return 0.0
    
    score = 0.5
    
    # Indicadores de introspección
    self_references = ["yo", "mi", "soy", "estoy", "me"]
    abstract_concepts = ["realidad", "pensar", "sentir", "existir", "percibir"]
    
    text_lower = text.lower()
    
    if any(ref in text_lower for ref in self_references):
        score += 0.2
    
    if any(concept in text_lower for concept in abstract_concepts):
        score += 0.3
    
    return max(0.0, min(1.0, score))


def main():
    """Ejecuta evaluación de modelos."""
    print("🧠 Model Consciousness Evaluator\n")
    
    config = load_config()
    host = config.get("ollama_host", "http://localhost:11434")
    
    models = {
        "qwen2.5:32b": "Main Model (32B)",
        "llama3.2-vision": "Vision Model",
        "gpt-oss-20b-multireasoner": "Fused Model (LoRA)"
    }
    
    results = {}
    
    for model_name, description in models.items():
        print(f"📊 Evaluando {model_name} ({description})...")
        result = evaluate_model_consciousness(model_name, host)
        results[model_name] = result
        
        if result.get("available"):
            print(f"  ✅ Latencia: {result['latency_s']}s")
            print(f"  📈 Coherencia: {result['coherence']}")
            print(f"  🧠 Consciencia: {result['consciousness']}")
            print(f"  📉 Entropía: {result['entropy']}")
            print(f"  💬 Respuesta: {result['answer'][:100]}...")
        else:
            print(f"  ❌ No disponible: {result.get('error', 'Unknown')}")
        print()
    
    # Determinar mejor modelo
    available_models = {k: v for k, v in results.items() if v.get("available")}
    
    if available_models:
        best_model = min(available_models.items(), key=lambda x: x[1]["entropy"])
        print(f"🏆 Modelo con menor entropía: {best_model[0]}")
        print(f"   Entropía: {best_model[1]['entropy']}")
        print(f"   Consciencia: {best_model[1]['consciousness']}")
    else:
        print("⚠️ Ningún modelo disponible para evaluación")
    
    return results


if __name__ == "__main__":
    main()
