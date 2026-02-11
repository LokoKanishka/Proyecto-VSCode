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
                pass
            
            data_int16 = (data * 32767).astype(np.int16)
            if len(data.shape) > 1:
                data_int16 = data_int16[:, 0] # mono
            
            ow_model.reset()
            
            chunk_size = 1280
            num_chunks = len(data_int16) // chunk_size
            
            clip_embeddings = []
            
            for i in range(num_chunks):
                chunk = data_int16[i*chunk_size : (i+1)*chunk_size]
                ow_model.predict(chunk)
                
                # Get embedding for this chunk (1, 96)
                # We flatten it to (96,)
                emb = ow_model.preprocessor.get_features()
                clip_embeddings.append(emb.flatten())
            
            # Now we need to create windows of 16 embeddings
            # openwakeword default models use a window of 16 frames (1.28s)
            # So our custom model input must be (16, 96) flattened -> 1536
            
            window_size = 16
            if len(clip_embeddings) < window_size:
                continue
                
            # Sliding window
            for i in range(len(clip_embeddings) - window_size + 1):
                window = clip_embeddings[i : i + window_size]
                # Concatenate all 16 embeddings -> (1536,)
                feature_vector = np.concatenate(window)
                
                # Labeling strategy:
                # If positive file, only windows near the end are positive?
                # Or all windows?
                # Simple approach: 
                # If label=1, assume the wake word is present in the clip.
                # But where? Usually these clips are short and contain the word.
                # Let's assume the word is centered or towards the end.
                # We'll take all windows for now, but maybe weight the end ones higher?
                # For simplicity: All windows from positive clips are positive.
                # (This might introduce noise if there's silence at start)
                
                features.append(feature_vector)
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
    
    # Define input as 2D initially for sklearn compatibility
    initial_type = [('float_input', FloatTensorType([None, X.shape[1]]))]
    
    # Disable zipmap to get tensor output for probabilities
    options = {id(clf): {'zipmap': False}}
    onnx_model = convert_sklearn(clf, initial_types=initial_type, options=options)
    
    # Post-process: Keep only the probability output
    if len(onnx_model.graph.output) > 1:
        onnx_model.graph.output.remove(onnx_model.graph.output[0])
        
    # -------------------------------------------------------------------------
    # CRITICAL FIX: Patch the ONNX model to accept 3D input (Batch, Time, Features)
    # openwakeword feeds (1, 16, 96) but our model expects (1, 1536).
    # We need to insert a Flatten node.
    # -------------------------------------------------------------------------
    import onnx
    from onnx import helper, TensorProto
    
    # 1. Change input shape to 3D [None, 16, 96]
    # We assume X.shape[1] is 1536, which is 16 * 96.
    n_frames = 16
    n_features = 96
    
    input_tensor = onnx_model.graph.input[0]
    input_tensor.type.tensor_type.shape.dim[0].dim_param = 'batch'
    input_tensor.type.tensor_type.shape.dim[1].dim_value = n_frames # 16
    # Add 3rd dimension
    dim3 = input_tensor.type.tensor_type.shape.dim.add()
    dim3.dim_value = n_features # 96
    
    # 2. Create a Flatten node
    # Input: 'float_input' (now 3D)
    # Output: 'flattened_input' (2D)
    flatten_node = helper.make_node(
        'Flatten',
        inputs=['float_input'],
        outputs=['flattened_input'],
        axis=1,
        name='Flatten_Input'
    )
    
    # 3. Insert the node at the beginning
    onnx_model.graph.node.insert(0, flatten_node)
    
    # 4. Rewire the original first node to use 'flattened_input'
    # The original first node (usually LinearClassifier or similar) used 'float_input'.
    # We need to find it and change its input.
    # Note: sklearn-onnx might produce a Scaler or ZipMap first.
    # We just look for any node consuming 'float_input' (except our new Flatten node)
    for node in onnx_model.graph.node:
        if node.name == 'Flatten_Input':
            continue
        for i, input_name in enumerate(node.input):
            if input_name == 'float_input':
                node.input[i] = 'flattened_input'
                
    # Save
    with open(OUTPUT_ONNX, "wb") as f:
        f.write(onnx_model.SerializeToString())
        
    log.info("¡Modelo guardado y parcheado exitosamente!")
    log.info("Ahora podés probarlo con el listener.")

if __name__ == "__main__":
    main()
