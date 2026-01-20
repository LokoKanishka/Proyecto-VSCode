import sys
import os
import time

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.engine.mock_engine import MockEngine

def test_mock_engine():
    print("Testing Mock Engine...")
    engine = MockEngine()
    
    print("1. Testing load_model...")
    success = engine.load_model("fake-model-v1")
    if success:
        print("Model loaded successfully [OK]")
    else:
        print("Model load failed [FAIL]")
        sys.exit(1)

    print("\n2. Testing generate_response (streaming)...")
    prompt = "Hello AI"
    stream = engine.generate_response(prompt)
    
    char_count = 0
    start_time = time.time()
    
    print("--- Stream Start ---")
    for char in stream:
        sys.stdout.write(char)
        sys.stdout.flush()
        char_count += 1
    print("\n--- Stream End ---")
    
    duration = time.time() - start_time
    print(f"\nStream complete. {char_count} chars in {duration:.2f}s [OK]")

if __name__ == "__main__":
    try:
        test_mock_engine()
    except KeyboardInterrupt:
        print("\nTest interrupted.")
