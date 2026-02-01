# Despliegue del Manager vLLM (≤ 20B)

Este documento recoge la receta operativa para correr el **manager principal de Lucy** usando modelos locales de hasta 20B parámetros (por ejemplo `gpt-oss:20b`) con cuantización AWQ y KV cache ajustado. El objetivo es cumplir con el plan maestro sin exceder los 32 GB de VRAM.

## 1. Requisitos

- Tener `vllm` instalado en la misma virtualenv que el resto del stack:  
  `pip install vllm` (preferible >=0.10).
- Descargar el modelo elegido (por ejemplo `gpt-oss:20b-awq`).  
  Si usás `ollama`, `ollama pull gpt-oss:20b` basta; el script lo apunta como `model` para vLLM.
- Asegurar que la GPU tenga los drivers y CUDA compatibles (CUDA 12.4 en Ubuntu 24.04).

## 2. Configuración de parámetros

El script `scripts/start_vllm_server.py` expone los parámetros clave:

| Variable | Significado | Valor sugerido |
| --- | --- | --- |
| `LUCY_VLLM_MODEL` | Modelo a cargar | `gpt-oss:20b` (default). |
| `LUCY_VLLM_MAX_CONTEXT` | Tokens máximos en el contexto | `16384` para evitar saturar el KV cache. |
| `LUCY_VLLM_QUANT` | Cuantización de pesos | `awq` (activa 4 bits con AWQ). |
| `LUCY_VLLM_GPU_MEM` | Fracción VRAM reservada para el modelo | `0.75`–`0.85` según uso; deja margen para workers. |
| `LUCY_VLLM_TENSOR_PARALLEL` | División tensorial | `1` en una sola RTX 5090. |

Adicionalmente, vLLM admite mecanismos de **quantized KV cache** para contextos extensos. Aunque el script no expone explícitamente ese flag, lo podemos activar editando la línea:

```python
cmd += ["--cache-quantization", "q8_0"]
```

si la versión de vLLM en uso lo soporta (consultá `vllm.entrypoints.openai.api_server --help`).

## 3. Inicio rápido

Activá el virtualenv y ejecutá:

```bash
export LUCY_VLLM_MODEL="gpt-oss:20b"
export LUCY_VLLM_MAX_CONTEXT="16384"
export LUCY_VLLM_QUANT="awq"
scripts/start_vllm_server.py --port 8000
```

El script inicia `vllm` en modo OpenAI-compatible; la API queda en `http://localhost:8000`. Lucy (manager y workers) puede apuntar a este host mediante `LUCY_VLLM_URL` o `config.yaml`.

## 4. Buenas prácticas

1. **Monitoreo de VRAM:** usá `nvidia-smi` en intervalos breves mientras se prueba la API para asegurarte que el modelo y el cache caben simultáneamente con los workers.
2. **Contextos largos:** si necesitás más de 16k tokens, habilitá cuantización de cache (Q8 o Q4) y bajá `LUCY_VLLM_MAX_CONTEXT` a lo realmente requerido (18k-20k).  
3. **Swapping coordinado:** el `ResourceManager` (ya implementado en el swarm runner) puede pausar la inferencia del manager y liberar los modelos auxiliares cuando no se usan.
4. **Documentar la política:** toda modificación de modelo debe registrarse en `docs/AGENT_PROGRESS.md` para evitar divergencias respecto al roadmap.

## 5. ¿Qué no hacemos?

- No cargamos modelos de 70B en producción: la estrategia es operar siempre con un modelo ≤ 20B (actualmente `gpt-oss:20b`) y, si se requiere capacidad extra, desplegar un worker especializado que cargue una LoRA únicamente cuando sea necesario.
- Seguimos manteniendo **soberanía digital**: el manager corre local, no se apoya en APIs privadas ni llaves externas.

