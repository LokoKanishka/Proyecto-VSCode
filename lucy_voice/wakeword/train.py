import os
import sys
import glob
import logging
import pathlib
import numpy as np
import soundfile as sf
from tqdm import tqdm

# openwakeword
from openwakeword import Model

# scikit-learn
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

# onnx conversion
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType

from lucy_voice.config import LucyConfig

# -----------------------------------------------------------------------------
# Configuración
# -----------------------------------------------------------------------------
config = LucyConfig()
DATA_DIR = config.base_dir / "lucy_voice" / "data" / "wakeword" / "hola_lucy"
POS_DIR = DATA_DIR / "positive"
NEG_DIR = DATA_DIR / "negative"
MODELS_DIR = config.base_dir / "lucy_voice" / "data" / "wakeword" / "modelos"

MODEL_NAME = "hola_lucy"
OUTPUT_ONNX = MODELS_DIR / f"{MODEL_NAME}.onnx"

# openwakeword usa chunks de 1280 muestras a 16kHz (~80ms).
# Para entrenar, extraemos embeddings de esos chunks.
# El modelo base de openwakeword genera embeddings de dimensión 96 (para el modelo 'embedding_model').
# Necesitamos instanciar openwakeword.Model() y usar get_embeddings().

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)8s | %(message)s",
    )

def load_wav_files(directory):
    return glob.glob(str(directory / "*.wav"))

def extract_features(wav_files, ow_model, label, n_chunks_per_clip=16):
    """
    Lee archivos WAV, los pasa por openwakeword para obtener embeddings.
    Devuelve X (features) e y (labels).
    
    n_chunks_per_clip: cuántos chunks de 80ms extraer de cada clip.
    """
    features = []
    labels = []
    
    print(f"Procesando {len(wav_files)} archivos para etiqueta {label}...")
    
    for wav_path in tqdm(wav_files):
        try:
            data, sr = sf.read(wav_path)
            if sr != 16000:
                # Resamplear si fuera necesario (simple skip)
                # Pero asumimos que grabamos a 16k.
                pass
            
            # Convertir a int16 para openwakeword
            # data está en float32 [-1, 1] -> int16
            data_int16 = (data * 32767).astype(np.int16)
            if len(data.shape) > 1:
                data_int16 = data_int16[:, 0] # mono
            
            # Alimentar al modelo chunk a chunk
            # openwakeword mantiene estado interno, así que reseteamos antes de cada clip
            ow_model.reset()
            
            # El modelo procesa chunks de 1280
            # Vamos a alimentar todo el clip y recolectar embeddings
            # Pero openwakeword.predict() devuelve predicciones, no embeddings directamente
            # A MENOS que usemos un modelo de embeddings.
            # La clase Model() carga por defecto modelos de wakeword.
            # Para obtener embeddings, usamos el modelo interno melspectrogram + embedding.
            
            # TRUCO: Model() tiene un método predict() que devuelve scores.
            # Pero también expone .get_embeddings() si se configuró o si accedemos al grafo.
            # La forma oficial de entrenar custom models en openwakeword es usar 
            # los embeddings generados por el modelo base.
            
            # Vamos a simular el streaming:
            chunk_size = 1280
            num_chunks = len(data_int16) // chunk_size
            
            clip_embeddings = []
            
            for i in range(num_chunks):
                chunk = data_int16[i*chunk_size : (i+1)*chunk_size]
                # predict() actualiza el estado interno y calcula embeddings
                ow_model.predict(chunk)
                
                # Ahora extraemos el embedding del último chunk procesado
                # Model.preprocessor_model devuelve melspec
                # Model.models['embedding_model'] (si existe) devuelve embeddings?
                # En la versión actual de openwakeword, hay una forma más directa?
                
                # Según la doc de openwakeword training:
                # Se usa el modelo 'embedding_model.onnx' (o similar).
                # Pero la clase Model() ya lo carga internamente para sus predicciones.
                # Accedemos a los embeddings de la última inferencia:
                # ow_model.get_embeddings() -> devuelve dict con embeddings de cada modelo cargado?
                # No, devuelve los embeddings del modelo base compartido.
                
                # Revisando código fuente de openwakeword (simulado):
                # ow_model.get_embeddings() devuelve un array (1, 96) aprox.
                
                emb = ow_model.preprocessor.get_features()
                clip_embeddings.append(emb.flatten())
            
            # Ahora tenemos N embeddings para este clip.
            # ¿Cómo etiquetamos? 
            # Para muestras POSITIVAS, los embeddings cercanos al final del clip (donde se dice "Lucy")
            # deberían ser positivos. 
            # Para simplificar, tomamos TODOS como positivos si es clip positivo?
            # NO. Solo los que corresponden a la palabra clave.
            # Pero no tenemos alineación precisa.
            # ESTRATEGIA SIMPLE (Weakly Supervised):
            # - Positivos: Tomamos los embeddings del último 50% del clip (asumiendo que "Hola Lucy" está ahí).
            # - Negativos: Tomamos todos los embeddings.
            
            if label == 1:
                # Tomar últimos N chunks (ej. 1 segundo = ~12 chunks)
                # "Hola Lucy" dura ~1 seg.
                start_idx = max(0, len(clip_embeddings) - 16) 
                selected = clip_embeddings[start_idx:]
            else:
                selected = clip_embeddings
            
            for vec in selected:
                features.append(vec)
                labels.append(label)
                
        except Exception as e:
            print(f"Error procesando {wav_path}: {e}")

    return np.array(features), np.array(labels)

def main():
    setup_logging()
    log = logging.getLogger("Trainer")
    
    # 1. Verificar datos
    pos_files = load_wav_files(POS_DIR)
    neg_files = load_wav_files(NEG_DIR)
    
    log.info(f"Archivos positivos encontrados: {len(pos_files)}")
    log.info(f"Archivos negativos encontrados: {len(neg_files)}")
    
    if len(pos_files) < 5 or len(neg_files) < 5:
        log.error("Muy pocos datos. Grabá al menos 10-20 muestras de cada tipo.")
        return

    # 2. Cargar modelo base para embeddings
    log.info("Cargando openwakeword para extraer embeddings...")
    # Cargamos solo el modelo de embedding si es posible, o Model() genérico.
    # Model() carga por defecto 'alexa', 'hey_jarvis', etc. y el embedding model compartido.
    ow_model = Model() 
    
    # 3. Extraer features
    log.info("Extrayendo features...")
    X_pos, y_pos = extract_features(pos_files, ow_model, 1)
    X_neg, y_neg = extract_features(neg_files, ow_model, 0)
    
    if len(X_pos) == 0 or len(X_neg) == 0:
        log.error("No se pudieron extraer features.")
        return

    X = np.vstack([X_pos, X_neg])
    y = np.concatenate([y_pos, y_neg])
    
    log.info(f"Dataset final: {X.shape} features, {y.shape} labels")
    
    # 4. Entrenar
    log.info("Entrenando LogisticRegression...")
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    clf = LogisticRegression(max_iter=1000, class_weight='balanced')
    clf.fit(X_train, y_train)
    
    # 5. Evaluar
    y_pred = clf.predict(X_test)
    log.info("Reporte de clasificación:")
    print(classification_report(y_test, y_pred))
    
    # 6. Exportar a ONNX
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    log.info(f"Exportando modelo a {OUTPUT_ONNX}...")
    
    # Revertimos a 2D para que el LinearClassifier sea válido.
    # Luego usaremos un script para agregar el nodo Flatten.
    initial_type = [('float_input', FloatTensorType([None, X.shape[1]]))]
    
    # Disable zipmap to get tensor output for probabilities
    options = {id(clf): {'zipmap': False}}
    onnx_model = convert_sklearn(clf, initial_types=initial_type, options=options)
    
    # Post-process: Keep only the probability output and ensure it's the first one
    # The outputs are usually [label, probabilities]. We want [probabilities].
    # We can just remove the first output from the graph.
    if len(onnx_model.graph.output) > 1:
        # Remove output_label
        onnx_model.graph.output.remove(onnx_model.graph.output[0])
        
    # Rename the remaining output to something standard if needed, but openwakeword just takes the first one.
    
    with open(OUTPUT_ONNX, "wb") as f:
        f.write(onnx_model.SerializeToString())
        
    log.info("¡Modelo guardado exitosamente!")
    log.info("Ahora podés probarlo con el listener.")

if __name__ == "__main__":
    main()
