import sounddevice as sd
import numpy as np
import scipy.io.wavfile as wav
import time

def list_devices():
    print("\n=== Audio Devices ===")
    print(sd.query_devices())
    print("=====================\n")

def test_recording():
    fs = 16000  # Sample rate
    seconds = 3  # Duration of recording

    print(f"Recording {seconds} seconds of audio...")
    print("PLEASE SPEAK NOW (Say 'Hola Lucy' or 'Testing')")
    
    myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    
    print("Recording finished.")
    
    # Check if audio is silent
    max_amp = np.max(np.abs(myrecording))
    print(f"Max Amplitude: {max_amp}")
    
    if max_amp == 0:
        print("ERROR: Recorded audio is completely silent!")
    elif max_amp < 100:
        print("WARNING: Audio is very quiet.")
    else:
        print("SUCCESS: Audio detected.")

    filename = "mic_test.wav"
    wav.write(filename, fs, myrecording)
    print(f"Saved to {filename}")

if __name__ == "__main__":
    try:
        list_devices()
        test_recording()
    except Exception as e:
        print(f"Error: {e}")
