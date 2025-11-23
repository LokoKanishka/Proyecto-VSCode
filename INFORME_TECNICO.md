# Informe Técnico: Fallo en Modelo de Wake Word "Hola Lucy"

**Fecha:** 22 de Noviembre de 2025
**Componente:** Lucy Voice / Wake Word Engine (`openwakeword`)
**Estado:** Crítico (Falsos positivos continuos)

## 1. Resumen del Problema
El sistema de detección de palabra clave ("Wake Word") personalizado para "Hola Lucy" presenta un comportamiento errático. Inicialmente fallaba por incompatibilidad de dimensiones (crash), y tras una corrección estructural, ahora genera **falsos positivos infinitos**, activándose constantemente con ruido ambiente o silencio.

## 2. Análisis de Causa Raíz

### A. Incompatibilidad de Tensores (Dimension Mismatch)
El problema fundamental es una discrepancia entre lo que la librería `openwakeword` entrega y lo que nuestro modelo personalizado espera:

*   **Salida de `openwakeword` (Runtime):** La librería procesa el audio y entrega "embeddings" (características numéricas) en un formato **3D**: `[Batch, Time, Features]`. Específicamente `[1, 16, 96]`. Esto representa 16 fragmentos de tiempo con 96 características cada uno.
*   **Entrada del Modelo Custom (Entrenamiento):** Nuestro modelo fue entrenado usando `scikit-learn` (Logistic Regression), que por definición trabaja con datos **2D**: `[Batch, Features]`. Durante el entrenamiento, aplanamos los datos a `[1, 1536]` (16 * 96).
*   **El Conflicto:** Al exportar a ONNX, el modelo quedó "rígido" esperando 2D. Cuando `openwakeword` le inyecta 3D, el motor de inferencia (ONNX Runtime) fallaba con `Invalid Rank`.

### B. Fallo en la Estrategia de "Parcheo"
Para solucionar el crash anterior, modificamos el archivo ONNX inyectando un nodo `Flatten` al inicio del grafo.
*   **Resultado:** El modelo ya no crashea porque el nodo `Flatten` convierte el `[1, 16, 96]` a `[1, 1536]`.
*   **Efecto Secundario:** Aunque las dimensiones coinciden, el modelo ahora predice la clase "1" (Activación) casi el 100% del tiempo. Esto sugiere que:
    1.  **Alineación de Features:** El aplanado en tiempo real podría no estar respetando el orden exacto que el modelo aprendió durante el entrenamiento.
    2.  **Overfitting (Sobreajuste):** El modelo se entrenó con muy pocas muestras (~24 audios). Es probable que haya aprendido "ruido" específico de esas muestras y ahora cualquier entrada se clasifica erróneamente como positiva.

## 3. Acciones Realizadas
1.  **Re-entrenamiento:** Se generó un nuevo modelo `hola_lucy.onnx` usando los audios disponibles en `lucy_voice/data/wakeword`.
2.  **Parcheo ONNX:** Se inyectó código en `train.py` para modificar el grafo ONNX y aceptar entradas 3D.
3.  **Lógica de Filtrado:** Se actualizó `wakeword_node.py` para ignorar explícitamente la clase "0" (ruido) y mapear la clase "1" a "hola_lucy".

## 4. Análisis Externo (ChatGPT Advanced)

Se consultó con otra IA avanzada que confirmó el diagnóstico y agregó detalles críticos:

### Confirmación del Problema
1. **Datos insuficientes:** ~24 clips es extremadamente poco. OpenWakeWord recomienda "miles de ejemplos" y muchas horas de audio negativo.
2. **Etiquetado agresivo:** Marcar TODAS las ventanas de clips positivos como `label=1` incluye silencio, respiraciones y ruido pre/post wake word. El modelo aprende "cualquier cosa del entorno acústico de las grabaciones".
3. **Falta de VAD interno:** OpenWakeWord tiene `vad_threshold` y `enable_speex_noise_suppression` que filtran antes de la predicción.

### Solución Recomendada
**Corto plazo (implementado):**
- Revertir a modelos pre-entrenados (`wakeword_model_paths: []`)
- Agregar `vad_threshold=0.5` y `enable_speex_noise_suppression=True` al `Model()`
- Archivar `train.py` como `train_sklearn_legacy.py`

**Medio plazo:**
- Usar el flujo oficial de openWakeWord: `automatic_model_training_simple.ipynb`
- Generar dataset grande con TTS castellano + audio real negativo
- Exportar modelo ONNX que ya espera `(1, 16, 96)` sin parches

## 5. Conclusión Final
El parche de `Flatten` era **técnicamente correcto** para las dimensiones, pero el modelo sklearn está fundamentalmente limitado por:
- Dataset microscópico y mal etiquetado
- Arquitectura no alineada con las expectativas de openWakeWord

**Acción tomada:** Lucy vuelve a usar modelos pre-entrenados (inglés) mientras se prepara un entrenamiento profesional del modelo "Hola Lucy".
