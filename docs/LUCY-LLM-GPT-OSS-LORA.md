# LLM de Lucy – GPT-OSS 20B + LoRA multilingüe (11/12/2025)

## Objetivo
- Mantener un cerebro local y open-source para Lucy (voz + escritorio).
- Mejorar razonamiento, multilingüismo y uso de herramientas sin modificar el flujo actual (Ollama).
- Usar un LoRA especializado y fusionarlo con el modelo base GPT-OSS 20B.

## Modelo base
- **`openai/gpt-oss-20b`** (equivalente a `gpt-oss:20b` en Ollama).
- Elegido como base por:
  - Buen equilibrio entre calidad y tamaño para uso local en la 5090.
  - Licencia abierta y despliegue sencillo vía Ollama.
  - Comportamiento instruccional estable en español/inglés para tareas mixtas (voz, web, escritorio).

## Qué es el LoRA elegido
- **LoRA:** `YiwenX/gpt-oss-20b-multilingual-reasoner`
  - Base: GPT-OSS 20B.
  - Enfoque: razonamiento multilingüe, cadenas de pensamiento, seguir instrucciones largas.
  - Esperado: mayor tolerancia a texto “sucio” de STT y mejor planificación de acciones de agente.
  - Licencia: Apache-2.0 (compatible con uso local/offline).

## Por qué sirve para Lucy
- Refuerza razonamiento y CoT en español e inglés sin agregar servicios externos.
- Puede mejorar instrucciones de múltiples turnos y tool use (web/desktop) sin tocar prompts.
- Sigue 100% local: mismo backend Ollama, sin dependencias nuevas en producción.

## Estrategia de integración
- Mantener `gpt-oss:20b` limpio como modelo base de referencia.
- Fusionar el LoRA en un checkpoint nuevo (ej. `gpt-oss-20b-multireasoner-merged`) usando PEFT.
- Exponer el modelo fusionado vía el mismo mecanismo actual (Ollama) para seleccionarlo en config:
  - `llm_model: "gpt-oss:20b"` (base actual).
  - `llm_model: "gpt-oss-20b-multireasoner"` (fusionado, opcional).

## Flujo de trabajo (alto nivel)
1) Descargar base + LoRA (Hugging Face).
2) Fusionar con PEFT (`merge_and_unload`) y guardar en disco (Transformers + safetensors).
3) (Opcional) Crear un `Modelfile` de Ollama apuntando al directorio fusionado y registrarlo como `gpt-oss-20b-multireasoner`.

## Requisitos y entorno
- Hardware: ver `docs/SYSTEM-2025-11-15.md` (Ryzen 9 7950X, 128 GB RAM, RTX 5090 32 GB VRAM). Con 32 GB de VRAM debería caber completo; en CPU/mixto usar `--device-map auto` + `--dtype bfloat16`.
- Dependencias Python (en venv aparte): `transformers`, `peft`, `accelerate`, `torch` (CUDA).
- Almacenamiento: ~30–40 GB libres para base + LoRA + salida fusionada.

## Script de fusión
Archivo: `tools/merge_gpt_oss_lora.py`

Uso recomendado:
```bash
python tools/merge_gpt_oss_lora.py \
  --base openai/gpt-oss-20b \
  --lora YiwenX/gpt-oss-20b-multilingual-reasoner \
  --out ./models/gpt-oss-20b-multireasoner-merged \
  --dtype bfloat16 \
  --device-map auto
```

Qué hace:
- Carga el modelo base y el LoRA con `device_map` automático y dtype configurable.
- Fusiona el LoRA en los pesos base (`merge_and_unload`) y guarda en `--out` usando safetensors.
- Copia el tokenizer del modelo base al directorio de salida.

## Integración con Lucy (Ollama)
1) Crear un `Modelfile` (ejemplo) apuntando al modelo fusionado:
```
FROM ./models/gpt-oss-20b-multireasoner-merged
PARAMETER temperature 0.6
PARAMETER num_ctx 4096
```
2) Registrar en Ollama:
```bash
ollama create gpt-oss-20b-multireasoner -f Modelfile
```
3) Seleccionar el modelo en Lucy:
   - En `config.yaml`, setear `ollama_model: "gpt-oss-20b-multireasoner"` (o alternar entre base y fusionado).
   - En el nodo modular (`external/nodo-de-voz-modular-de-lucy/config.yaml`), usar el mismo nombre si se quiere que la voz use el modelo fusionado.

## Próximos pasos sugeridos
- Ejecutar el script de fusión en un venv con CUDA y validar con `ollama run gpt-oss-20b-multireasoner "Decime en una frase si estás listo"`.
- Medir latencia vs. `gpt-oss:20b` y documentar diferencias de comportamiento en `docs/ESTADO-LUCY-VOICE-*.md`.

## Limitaciones / riesgos
- Puede cambiar ligeramente el estilo de respuesta aun mejorando el razonamiento.
- La mejora en CoT no garantiza mejor desempeño en pedidos triviales.
- Probar exhaustivamente comandos de escritorio y tool use antes de hacerlo default.
