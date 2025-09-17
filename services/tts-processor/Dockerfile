# TTS-Processor Service Dockerfile
# Optimized for speed and minimal size - no heavy ML dependencies

FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies (minimal set)
RUN apt-get update && apt-get install -y \
    curl \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy requirements first for better caching
COPY services/tts-processor/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy service code
COPY services/tts-processor/config.py .
COPY services/tts-processor/audio_utils.py .
COPY services/tts-processor/tts_engine.py .
COPY services/tts-processor/redis_consumer.py .
COPY services/tts-processor/main.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash tts_user && \
    chown -R tts_user:tts_user /app

# Switch to non-root user
USER tts_user

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose service port
EXPOSE 8000

# Run the service
CMD ["python", "main.py"]

