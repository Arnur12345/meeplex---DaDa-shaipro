# TTS-Processor Service

A high-performance Text-to-Speech microservice designed for real-time audio generation from LLM responses in the Raven AI system.

## 🎯 Overview

The TTS-Processor service consumes LLM-generated responses from the `llm_responses` Redis stream and produces base64-encoded audio data to the `tts_audio_queue` stream for downstream consumption by the vexa-bot.

## 🚀 Features

- **Fast Audio Generation**: Optimized for <3 second response time
- **Multiple TTS Engines**: gTTS (primary), pyttsx3 (fallback)
- **In-Memory Processing**: No file system dependency for better performance
- **Redis Stream Integration**: Seamless message flow with error handling
- **Lightweight Architecture**: Minimal dependencies, optimized container size
- **Health Monitoring**: Comprehensive health checks and statistics
- **Automatic Retries**: Robust error handling with retry logic

## 📋 Architecture

### Message Flow
```
LLM-Processor → llm_responses stream → TTS-Processor → tts_audio_queue stream → Vexa-Bot
```

### TTS Engines
1. **gTTS (Primary)**: Google Text-to-Speech
   - Fast, reliable, cloud-based
   - High-quality audio output
   - Requires internet connection

2. **pyttsx3 (Fallback)**: Offline TTS
   - Works without internet
   - Lower quality but reliable
   - Local processing

### Audio Processing
- **Format**: MP3 (base64 encoded)
- **Bitrate**: 64kbps (optimized for streaming)
- **Sample Rate**: 22050 Hz
- **Encoding**: Base64 for Redis stream compatibility

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | `redis` | Redis server hostname |
| `REDIS_PORT` | `6379` | Redis server port |
| `REDIS_INPUT_STREAM_NAME` | `llm_responses` | Input stream name |
| `REDIS_OUTPUT_STREAM_NAME` | `tts_audio_queue` | Output stream name |
| `TTS_ENGINE` | `gtts` | Primary TTS engine |
| `TTS_LANGUAGE` | `en` | Default language |
| `TTS_TIMEOUT` | `10` | TTS generation timeout (seconds) |
| `MAX_TEXT_LENGTH` | `1000` | Maximum text length |
| `FASTAPI_PORT` | `8000` | Service port |

### Stream Configuration
- **Consumer Group**: `tts_processor_group`
- **Block Time**: 2000ms
- **Batch Size**: 10 messages
- **Retry Attempts**: 3

## 🏃‍♂️ Usage

### Docker Compose
```bash
# Start the service
docker compose up tts-processor

# Check health
make tts-health

# View logs
make tts-logs

# Test generation
make tts-test
```

### Direct API Usage
```bash
# Generate audio
curl -X POST http://localhost:8125/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello world!", "language": "en"}'

# Check health
curl http://localhost:8125/health

# Get statistics
curl http://localhost:8125/stats
```

## 📊 API Endpoints

### `POST /generate`
Generate TTS audio from text
```json
{
  "text": "Hello, world!",
  "language": "en",
  "voice_options": {}
}
```

### `GET /health`
Service health check
```json
{
  "status": "healthy",
  "tts_ready": true,
  "redis_connected": true,
  "engine_status": {...}
}
```

### `GET /stats`
Processing statistics
```json
{
  "engine_status": {
    "generations": 42,
    "successes": 40,
    "failures": 2,
    "avg_duration": 1.5
  },
  "stream_info": {...}
}
```

### `GET /engines`
List available TTS engines
```json
{
  "engines": ["gtts", "pyttsx3"],
  "status": {...}
}
```

## 🔄 Message Format

### Input (`llm_responses` stream)
```json
{
  "response": "The current time is 3:30 PM",
  "session_uid": "session-123",
  "meeting_id": "meeting-456",
  "original_question": "what time is it",
  "timestamp": "2025-09-16T15:30:00Z"
}
```

### Output (`tts_audio_queue` stream)
```json
{
  "audio_data": "base64_encoded_mp3_data",
  "audio_metadata": {
    "format": "mp3",
    "size_bytes": 8192,
    "duration_seconds": 2.5,
    "engine": "gtts"
  },
  "session_uid": "session-123",
  "meeting_id": "meeting-456",
  "original_question": "what time is it",
  "response_text": "The current time is 3:30 PM",
  "timestamp": "2025-09-16T15:30:05Z"
}
```

## 🔧 Management Commands

```bash
# Health and Status
make tts-health          # Check service health
make tts-stats           # Get processing statistics
make tts-engines         # List available engines

# Testing
make tts-test            # Test audio generation
make tts-streams         # Monitor Redis streams
make tts-pipeline-test   # Test full LLM→TTS pipeline

# Management
make tts-logs            # View service logs
make tts-restart         # Restart service
```

## 📈 Performance

### Target Metrics
- **Response Time**: <3 seconds end-to-end
- **Throughput**: 10+ requests/second
- **Availability**: 99.9%
- **Audio Quality**: Clear, understandable speech

### Optimizations
- In-memory processing (no file I/O)
- Async processing pipeline
- Connection pooling
- Lightweight dependencies
- Efficient audio encoding

## 🚨 Monitoring

### Health Checks
- Redis connectivity
- TTS engine availability
- Audio generation test
- Stream processing status

### Logging
- Structured logging with context
- Performance metrics
- Error tracking
- Request tracing

### Metrics
- Generation count/success rate
- Average processing time
- Stream message rates
- Engine usage statistics

## 🔍 Troubleshooting

### Common Issues

1. **Audio Generation Fails**
   - Check internet connectivity (for gTTS)
   - Verify TTS engine status: `make tts-engines`
   - Check service logs: `make tts-logs`

2. **Redis Connection Issues**
   - Verify Redis is running: `docker compose ps redis`
   - Check network connectivity
   - Review Redis configuration

3. **High Latency**
   - Monitor with: `make tts-stats`
   - Check system resources
   - Consider scaling horizontally

### Debug Commands
```bash
# Check service status
make tts-health

# Monitor stream processing
make tts-streams

# Test individual components
make tts-test

# Full pipeline test
make tts-pipeline-test
```

## 🔐 Security

- Non-root container execution
- Input validation and sanitization
- Rate limiting (inherited from Redis)
- No persistent data storage
- Minimal attack surface

## 📦 Dependencies

### Core Dependencies
- `fastapi`: Web framework
- `redis[hiredis]`: Redis client with C extensions
- `gtts`: Google Text-to-Speech
- `pyttsx3`: Offline TTS engine
- `aiohttp`: Async HTTP client

### System Requirements
- Python 3.10+
- Internet access (for gTTS)
- Redis server
- ~100MB memory
- ~50MB disk space

## 🚀 Scaling

### Horizontal Scaling
- Multiple TTS processor instances
- Redis consumer groups for load balancing
- Load-based auto-scaling

### Performance Tuning
- Adjust batch sizes and timeouts
- Optimize Redis connection pools
- Configure engine preferences
- Monitor resource usage

## 📝 Development

### Local Development
```bash
cd services/tts-processor
pip install -r requirements.txt
python main.py
```

### Testing
```bash
# Unit tests
pytest tests/

# Integration tests
make tts-pipeline-test

# Load testing
# (Use external load testing tools)
```

## 🤝 Integration

The TTS-Processor service integrates with:
- **LLM-Processor**: Consumes generated responses
- **Vexa-Bot**: Provides audio for playback
- **Redis**: Message streaming and coordination
- **Monitoring**: Health checks and metrics

## 📚 Related Documentation

- [Phase 4 Implementation Guide](../../.cursorrules)
- [LLM-Processor Documentation](../llm-processor/README.md)
- [Redis Stream Architecture](../../docs/)
- [Docker Compose Configuration](../../docker-compose.yml)


