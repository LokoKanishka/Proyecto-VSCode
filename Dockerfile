FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Install System Dependencies
RUN apt-get update && apt-get install -y \
    python3.12 python3.12-dev python3-pip \
    git curl ffmpeg tesseract-ocr \
    xdotool libgl1-mesa-glx libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Set python3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install Node.js for UI building (if needed in container)
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs

# Set Working Directory
WORKDIR /app

# Install Python Deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir ray[default] lancedb pynvml loguru openai mss pyautogui overrides

# Copy Code
COPY . .

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default Command
CMD ["python3", "lucy_ignition.py"]
