# Multi-stage Dockerfile for LLM-Processor with Ollama and Mistral 7B
FROM ollama/ollama:latest as ollama-base

# Python runtime stage
FROM python:3.10-slim as python-base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN useradd --create-home --shell /bin/bash ollama

# Copy Ollama binary from ollama-base
COPY --from=ollama-base /bin/ollama /usr/local/bin/ollama

# Set up working directory
WORKDIR /app

# Copy Python requirements and install dependencies
COPY services/llm-processor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY services/llm-processor/ .

# Debug: List files to verify they were copied
RUN ls -la /app/
RUN echo "Python version:" && python --version
RUN echo "Python path:" && python -c "import sys; print(sys.path)"
RUN echo "Testing imports:" && python -c "import config; print('config imported successfully')" || echo "config import failed"
RUN echo "Testing main.py:" && python -c "import main; print('main imported successfully')" || echo "main import failed"

# Create directory for Ollama models
RUN mkdir -p /home/ollama/.ollama && \
    chown -R ollama:ollama /home/ollama

# Create startup script
RUN printf '#!/bin/bash\n\
set -e\n\
\n\
echo "Starting LLM-Processor service..."\n\
\n\
# Start Ollama server in background\n\
echo "Starting Ollama server..."\n\
su ollama -c "ollama serve" &\n\
OLLAMA_PID=$!\n\
\n\
# Wait for Ollama to be ready\n\
echo "Waiting for Ollama to be ready..."\n\
for i in {1..30}; do\n\
    if curl -f http://localhost:11434/api/tags >/dev/null 2>&1; then\n\
        echo "Ollama is ready!"\n\
        break\n\
    fi\n\
    if [ $((i %% 5)) -eq 0 ]; then\n\
        echo "Waiting for Ollama... ($i/30)"\n\
    fi\n\
    sleep 2\n\
done\n\
\n\
# Check if Ollama is ready\n\
if ! curl -f http://localhost:11434/api/tags >/dev/null 2>&1; then\n\
    echo "Ollama failed to start properly"\n\
    exit 1\n\
fi\n\
\n\
# Function to cleanup on exit\n\
cleanup() {\n\
    echo "Shutting down services..."\n\
    kill $OLLAMA_PID 2>/dev/null || true\n\
    wait $OLLAMA_PID 2>/dev/null || true\n\
}\n\
trap cleanup EXIT\n\
\n\
# Start FastAPI application\n\
echo "Starting FastAPI application..."\n\
python main.py\n' > /app/start.sh

RUN chmod +x /app/start.sh

# Health check script
RUN printf '#!/bin/bash\n\
# Check if both Ollama and FastAPI are responding\n\
curl -f http://localhost:11434/api/tags >/dev/null 2>&1 && \\\n\
curl -f http://localhost:8000/health >/dev/null 2>&1\n' > /app/healthcheck.sh

RUN chmod +x /app/healthcheck.sh

# Set user and expose ports
USER root
EXPOSE 8000 11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD /app/healthcheck.sh

# Start the service
CMD ["/app/start.sh"]
