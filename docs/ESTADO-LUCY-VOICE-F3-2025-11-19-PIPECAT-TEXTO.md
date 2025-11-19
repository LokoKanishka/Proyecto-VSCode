# ESTADO LUCY VOZ – Fase 3 (Pipecat + wakeword) – 2025-11-19

## 1. Resumen de lo logrado

En esta jornada se avanzó en dos frentes principales:

1. **Wake word “hola Lucy” (dataset local)**  
   - Se creó la estructura de datos para el entrenamiento del wake word propio:
     - `lucy_voice/data/wakeword/hola_lucy/positive/`
     - `lucy_voice/data/wakeword/hola_lucy/negative/`
   - Se implementaron dos grabadores:
     - `record_wakeword_samples.py` → graba muestras **positivas** diciendo “hola Lucy”.
     - `record_wakeword_negatives.py` → graba muestras **negativas** (ruido, otras frases).
   - Se agregó `lucy_voice/data/wakeword/` al `.gitignore` para que los audios **no se suban** al repo.
   - Se registró la dependencia de audio `soundfile` en `lucy_voice/requirements.txt`.

2. **Esqueleto de grafo Pipecat con LLM de texto**  
   - Se dejó de usar el viejo `pipecat_graph_stub.py` como única referencia y se creó:
     - `lucy_voice/pipecat_graph.py` → fábrica del `Pipeline` real de Lucy.
   - Se implementaron procesadores específicos de Lucy:
     - `LucyOllamaTextLLMProcessor`  
       - Recibe `TextFrame` con texto de usuario (dirección downstream).
       - Arma un prompt estilo Lucy (castellano rioplatense, respuestas breves).
       - Llama a Ollama vía CLI usando el modelo configurado (`LucyPipelineConfig.llm_model`, por defecto `gpt-oss:20b`).
       - Genera otro `TextFrame` con la respuesta del modelo.
     - `LucyConsoleTextOutputProcessor`  
       - Imprime en consola cualquier `TextFrame` que reciba, con un prefijo (`[LucyPipecat-TextOut]`).
       - Sirve para depurar el flujo de texto dentro del pipeline.

## 2. Estado actual del grafo Pipecat

El nuevo `build_lucy_pipeline(config)` (en `pipecat_graph.py`):

- Verifica que Pipecat esté disponible.
- Lee el modelo a usar desde `config.llm_model` (tipo `LucyPipelineConfig`).
- Construye un `Pipeline` con esta cadena de procesadores:

```text
Pipeline#0::Source
  → LucyOllamaTextLLMProcessor (LLM local vía Ollama)
  → LucyConsoleTextOutputProcessor ( salida a consola )
  → Pipeline#0::Sink
