import psutil
import time
import os

def profile_system():
    print("📊 Monitoring System Resources (Ctrl+C to stop)...")
    try:
        while True:
            cpu = psutil.cpu_percent(interval=1)
            mem = psutil.virtual_memory()
            
            # GPU Monitoring (Mock if pynvml fails/not installed)
            gpu_info = "N/A"
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                gpu_info = f"GPU: {util.gpu}% | VRAM: {mem_info.used / 1024**2:.0f}MB / {mem_info.total / 1024**2:.0f}MB"
            except ImportError:
                 gpu_info = "GPU: (pynvml missing)"
            except Exception:
                 gpu_info = "GPU: (Error)"

            print(f"🖥️ CPU: {cpu}% | 🧠 RAM: {mem.percent}% ({mem.used / 1024**3:.1f}GB) | {gpu_info}")
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Profiling stopped.")

if __name__ == "__main__":
    profile_system()
