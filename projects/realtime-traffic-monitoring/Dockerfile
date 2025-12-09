FROM python:3.9-slim

WORKDIR /app

# Install system dependencies for OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt kafka-python

# Copy project files
COPY . .

# Create output directories
RUN mkdir -p images inference_results

# Default command (can be overridden in docker-compose)
CMD ["python", "kafka_producer.py"]
