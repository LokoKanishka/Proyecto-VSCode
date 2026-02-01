FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

# Install System Dependencies
RUN apt-get update && apt-get install -y \
    python3.10 python3-pip python3.10-dev \
    git curl ffmpeg tesseract-ocr \
    xdotool libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Set Working Directory
WORKDIR /app

# Install Python Deps
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt
RUN pip3 install --no-cache-dir ray[default] "ray[serve]" pytesseract reportlab psutil pynvml

# Copy Code
COPY . .

# Environment
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default Command (Overridden by Compose)
CMD ["python3", "-m", "src.main"]
