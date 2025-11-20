import onnxruntime as ort
import sys

model_path = "lucy_voice/data/wakeword/modelos/hola_lucy.onnx"

try:
    sess = ort.InferenceSession(model_path)
    print("Inputs:")
    for i in sess.get_inputs():
        print(f"  Name: {i.name}, Type: {i.type}, Shape: {i.shape}")
    
    print("\nOutputs:")
    for o in sess.get_outputs():
        print(f"  Name: {o.name}, Type: {o.type}, Shape: {o.shape}")

except Exception as e:
    print(f"Error loading model: {e}")
