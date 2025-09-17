# LLM-Processor Service

The LLM-Processor service is a FastAPI-based microservice that provides "Hey, Raven" wake word detection and LLM response generation using Ollama with Mistral 7B.

## Overview

This service integrates with the Raven AI transcription system to:
1. Consume wake word commands from the `hey_raven_commands` Redis stream
2. Generate intelligent responses using Ollama's Mistral 7B model
3. Publish responses to the `llm_responses` Redis stream for TTS processing

## Architecture

```
Transcription → Wake Word Detection → LLM Processing → TTS
     ↓              ↓                    ↓             ↓
Redis Stream:  hey_raven_commands → llm_responses → tts_audio_queue
```

## Features

- **Wake Word Detection**: Integrated with transcription-collector for "Hey Raven" commands
- **LLM Integration**: Uses Ollama with Mistral 7B for response generation
- **Redis Streams**: Reliable message processing with acknowledgments
- **Health Monitoring**: Comprehensive health checks for Ollama and Redis
- **GPU Support**: CUDA acceleration for model inference
- **Error Recovery**: Retry logic and stale message handling

## Configuration

Environment variables:

### Redis Configuration
- `REDIS_HOST`: Redis server host (default: "redis")
- `REDIS_PORT`: Redis server port (default: 6379)
- `REDIS_DB`: Redis database number (default: 0)
- `REDIS_INPUT_STREAM_NAME`: Input stream name (default: "hey_raven_commands")
- `REDIS_OUTPUT_STREAM_NAME`: Output stream name (default: "llm_responses")
- `REDIS_CONSUMER_GROUP`: Consumer group name (default: "llm_processor_group")

### Ollama Configuration
- `OLLAMA_HOST`: Ollama server host (default: "localhost")
- `OLLAMA_PORT`: Ollama server port (default: 11434)
- `OLLAMA_MODEL`: Model name (default: "mistral:7b")
- `OLLAMA_API_TIMEOUT`: API timeout in seconds (default: 60)
- `OLLAMA_MAX_RETRIES`: Max retry attempts (default: 3)

### Response Configuration
- `MAX_RESPONSE_LENGTH`: Maximum response length (default: 500)
- `RESPONSE_TEMPERATURE`: LLM temperature (default: 0.7)
- `RAVEN_PERSONALITY_PROMPT`: System prompt for Raven personality

### FastAPI Configuration
- `FASTAPI_HOST`: Server host (default: "0.0.0.0")
- `FASTAPI_PORT`: Server port (default: 8000)
- `LOG_LEVEL`: Logging level (default: "INFO")

### Model Pull Configuration
- `MODEL_PULL_VERBOSE`: Enable verbose model pull logging (default: "false")
- `MODEL_PULL_PROGRESS_INTERVAL`: Log every Nth progress update (default: "10")

## API Endpoints

### Health Check
```
GET /health
```
Returns service health status including Ollama and Redis connectivity.

### List Models
```
GET /models
```
Lists available models in Ollama.

### Generate Response (Testing)
```
POST /generate
Content-Type: application/json

{
  "question": "What is the weather like?",
  "context": "Meeting discussion about outdoor events"
}
```

### Root
```
GET /
```
Service information and available endpoints.

## Wake Word Patterns

The service detects the following wake word patterns (case-insensitive):
- "hey raven"
- "hello raven"
- "raven," (with comma)
- "raven can/could/will/would/please"
- "raven what/where/when/who/why/how"
- "raven?" (with question mark)

## Message Format

### Input Stream (`hey_raven_commands`)
```json
{
  "payload": {
    "question": "What is the agenda for today?",
    "session_uid": "session_123",
    "meeting_id": 456,
    "context": "Meeting segment at 120.5s",
    "timestamp": "2025-01-01T10:00:00Z",
    "type": "wake_word_command"
  }
}
```

### Output Stream (`llm_responses`)
```json
{
  "payload": {
    "response": "Today's agenda includes project updates and quarterly planning.",
    "session_uid": "session_123",
    "meeting_id": 456,
    "original_question": "What is the agenda for today?",
    "timestamp": "2025-01-01T10:00:01Z",
    "original_timestamp": "2025-01-01T10:00:00Z",
    "message_id": "response_uuid_123"
  }
}
```

## Docker Deployment

The service is designed to run in Docker with multi-stage builds:

1. **Ollama Stage**: Copies Ollama binary from official image
2. **Python Stage**: Sets up FastAPI application with dependencies
3. **Runtime**: Runs both Ollama server and FastAPI application

### GPU Support
Requires NVIDIA Docker runtime and GPU allocation in docker-compose.yml:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          device_ids: ["0"]
          capabilities: [gpu]
```

## Development

### Local Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Start Redis (required)
docker run -d -p 6379:6379 redis:7.0-alpine

# Start Ollama (required)
ollama serve
ollama pull mistral:7b

# Run the service
python main.py
```

### Testing
```bash
# Test health endpoint
curl http://localhost:8000/health

# Test generation endpoint
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello Raven, how are you?"}'
```

## Monitoring

The service provides comprehensive logging and health checks:
- Service startup/shutdown events
- Redis stream processing metrics
- Ollama model initialization status
- Error tracking with retry attempts
- Performance metrics for response generation

## Integration

This service integrates with:
- **transcription-collector**: Receives wake word commands
- **TTS service**: Provides responses for audio generation
- **Redis**: Message broker for reliable communication
- **Ollama**: LLM inference engine

## Troubleshooting

### Common Issues

1. **Ollama Model Not Found**
   - Check if Mistral 7B is pulled: `ollama list`
   - Verify model name in configuration
   - Check GPU memory availability

2. **Redis Connection Issues**
   - Verify Redis is running and accessible
   - Check Redis host/port configuration
   - Monitor Redis stream lengths

3. **Wake Word Not Detected**
   - Check transcription-collector logs
   - Verify wake word patterns in transcription text
   - Monitor `hey_raven_commands` stream

4. **GPU Issues**
   - Verify NVIDIA Docker runtime is installed
   - Check GPU device allocation in docker-compose
   - Monitor GPU memory usage

### Logs
Service logs include:
- `[WakeWord Detected]`: Wake word detection events
- `[LLM Generation]`: Response generation metrics
- `[Redis Stream]`: Stream processing events
- `[Health Check]`: Service health status
