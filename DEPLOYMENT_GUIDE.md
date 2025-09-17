# Hey Raven Voice Assistant - Complete Deployment Guide

This guide covers the complete deployment of the "Hey Raven" voice assistant system from Phases 1-8.

## 🎯 System Overview

Hey Raven is a comprehensive voice assistant that integrates into video meetings and provides intelligent, context-aware responses. The system consists of:

1. **Transcription Collection** - Wake word detection and speech processing
2. **LLM Processing** - Context-aware response generation with multi-language support
3. **TTS Generation** - High-quality text-to-speech with audio optimization
4. **Vexa-Bot Integration** - Meeting participation and audio playback
5. **Monitoring & Analytics** - Comprehensive metrics and performance tracking

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Ollama with appropriate model
- Redis server
- WhisperLive service
- 4GB+ RAM, 2+ CPU cores
- Network access for video meeting platforms

### 1. Environment Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd raven_ai

# Copy environment template
cp raven_api/env-example.hey-raven raven_api/.env

# Edit configuration
nano raven_api/.env
```

### 2. Configuration

#### Required Environment Variables

```bash
# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0

# LLM Configuration
OLLAMA_HOST=localhost
OLLAMA_PORT=11434
OLLAMA_MODEL=mistral:7b

# TTS Configuration
TTS_ENGINE=gtts
TTS_LANGUAGE=en

# Audio Configuration
TTS_AUDIO_STREAM_NAME=tts_audio_queue
REDIS_INPUT_STREAM_NAME=hey_raven_commands
REDIS_OUTPUT_STREAM_NAME=llm_responses
```

### 3. Deployment

#### Option A: Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

#### Option B: Manual Deployment

```bash
# Start Redis
redis-server

# Start Ollama
ollama serve

# Start individual services
cd raven_api/services/transcription-collector && python main.py &
cd raven_api/services/llm-processor && python main.py &
cd raven_api/services/tts-processor && python main.py &
cd raven_api/services/bot-manager && python main.py &
```

### 4. Validation

```bash
# Run configuration validation
cd raven_api
python scripts/validate_config.py --env-file .env

# Run integration tests
python -m pytest tests/integration/test_hey_raven_workflow.py -v

# Test individual services
curl http://localhost:8000/health  # TTS service
curl http://localhost:11434/api/tags  # Ollama
```

## 📋 Detailed Deployment Steps

### Phase 1-2: Core Infrastructure

#### Transcription Collector Setup

```bash
cd raven_api/services/transcription-collector

# Install dependencies
pip install -r requirements.txt

# Configure wake word detection
cp config/wake_word_config.json.example config/wake_word_config.json
nano config/wake_word_config.json

# Start service
python main.py
```

#### LLM Processor Setup

```bash
cd raven_api/services/llm-processor

# Install dependencies
pip install -r requirements.txt

# Ensure Ollama model is available
ollama pull mistral:7b

# Start service
python main.py
```

### Phase 3-4: TTS and Audio

#### TTS Processor Setup

```bash
cd raven_api/services/tts-processor

# Install dependencies
pip install -r requirements.txt

# Test TTS generation
python -c "
from tts_engine import RavenTTSEngine
engine = RavenTTSEngine()
audio_data = engine.generate_speech('Hello, this is a test')
print(f'Generated {len(audio_data)} bytes of audio')
"

# Start service
python main.py
```

### Phase 5-6: Vexa-Bot Integration

#### Bot Manager Setup

```bash
cd raven_api/services/bot-manager

# Install dependencies
pip install -r requirements.txt

# Configure bot settings
nano app/config.py

# Start service
python app/main.py
```

#### Vexa-Bot Setup

```bash
cd raven_api/services/vexa-bot

# Install Node.js dependencies
npm install

# Build TypeScript
npm run build

# Test bot functionality
npm test

# Deploy bot (this will vary by deployment target)
./test-bot.sh
```

### Phase 7-8: Advanced Features

#### Monitoring Setup

```bash
cd raven_api/monitoring

# Install monitoring dependencies
pip install redis matplotlib asyncio

# Start metrics collector
python metrics_collector.py &

# View performance dashboard
# (Integration with Grafana/Prometheus recommended)
```

#### Multi-language Configuration

Update your environment file:

```bash
# Add language support
SUPPORTED_LANGUAGES=en,es,fr,de,it,pt,ja,zh
DEFAULT_LANGUAGE=en
AUTO_DETECT_LANGUAGE=true
```

## 🔧 Configuration Details

### Wake Word Detection

Configure wake word patterns in `config/wake_word_config.json`:

```json
{
  "patterns": {
    "en": ["hey raven", "hello raven", "raven"],
    "es": ["hola raven", "oye raven"],
    "fr": ["bonjour raven", "salut raven"]
  },
  "sensitivity": 0.7,
  "rate_limiting": {
    "max_requests_per_minute": 10,
    "cooldown_seconds": 2
  }
}
```

### LLM Response Configuration

```bash
# Response quality settings
MAX_RESPONSE_LENGTH=500
RESPONSE_TEMPERATURE=0.7
RAVEN_PERSONALITY_PROMPT="You are Raven, a helpful AI assistant..."

# Context settings
CONTEXT_HISTORY_LENGTH=10
MEETING_CONTEXT_ENABLED=true
```

### TTS Audio Settings

```bash
# Audio quality
TTS_AUDIO_FORMAT=mp3
AUDIO_SAMPLE_RATE=22050
AUDIO_BITRATE=64k

# Performance
TTS_TIMEOUT=10
TTS_RETRY_ATTEMPTS=3
MAX_AUDIO_DURATION=30
```

### Performance Tuning

```bash
# Redis stream settings
REDIS_STREAM_READ_COUNT=10
REDIS_STREAM_BLOCK_MS=2000

# Ollama optimization
OLLAMA_API_TIMEOUT=60
OLLAMA_MAX_RETRIES=3

# Bot performance
RECONNECTION_INTERVAL_MS=5000
```

## 🔍 Monitoring and Debugging

### Health Checks

Each service provides health endpoints:

```bash
# Check service health
curl http://localhost:8000/health      # TTS Processor
curl http://localhost:8001/health      # LLM Processor
curl http://localhost:8002/health      # Transcription Collector
curl http://localhost:8003/health      # Bot Manager
```

### Log Analysis

```bash
# View service logs
docker-compose logs transcription-collector
docker-compose logs llm-processor
docker-compose logs tts-processor
docker-compose logs vexa-bot

# Real-time monitoring
docker-compose logs -f --tail=100
```

### Performance Metrics

Monitor key metrics:

- **End-to-end response time**: < 5 seconds target
- **Wake word accuracy**: > 95%
- **TTS generation time**: < 2 seconds
- **Audio playback latency**: < 1 second
- **Service uptime**: > 99.9%

### Redis Stream Monitoring

```bash
# Monitor stream activity
redis-cli XINFO STREAM hey_raven_commands
redis-cli XINFO STREAM llm_responses
redis-cli XINFO STREAM tts_audio_queue

# Check consumer groups
redis-cli XINFO GROUPS hey_raven_commands
```

## 🛠️ Troubleshooting

### Common Issues

#### 1. Wake Word Not Detected

```bash
# Check transcription service
curl -X POST http://localhost:8002/test-wake-word \
  -H "Content-Type: application/json" \
  -d '{"text": "Hey Raven, what time is it?"}'

# Verify wake word config
cat raven_api/services/transcription-collector/config/wake_word_config.json
```

#### 2. LLM Not Responding

```bash
# Test Ollama directly
curl http://localhost:11434/api/generate \
  -d '{"model": "mistral:7b", "prompt": "Hello", "stream": false}'

# Check Redis streams
redis-cli XLEN hey_raven_commands
redis-cli XLEN llm_responses
```

#### 3. TTS Audio Issues

```bash
# Test TTS service
curl -X POST http://localhost:8000/generate-tts \
  -H "Content-Type: application/json" \
  -d '{"text": "This is a test", "session_id": "test123"}'

# Check audio format support
python -c "
import gtts
tts = gtts.gTTS('test')
print('TTS working')
"
```

#### 4. Bot Connection Issues

```bash
# Check bot manager
curl http://localhost:8003/bots

# Verify vexa-bot build
cd raven_api/services/vexa-bot
npm run build
npm test
```

### Performance Issues

#### High Latency

1. Check Redis connection latency
2. Optimize Ollama model settings
3. Reduce TTS audio quality if needed
4. Enable caching for repeated requests

#### Memory Usage

1. Monitor Redis memory usage
2. Limit conversation history length
3. Clean up old session data
4. Optimize audio buffer sizes

## 🚀 Production Deployment

### Docker Production Setup

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  redis:
    image: redis:7-alpine
    restart: always
    volumes:
      - redis_data:/data

  transcription-collector:
    build: ./services/transcription-collector
    restart: always
    depends_on:
      - redis
    environment:
      - LOG_LEVEL=INFO
      - REDIS_HOST=redis

  llm-processor:
    build: ./services/llm-processor
    restart: always
    depends_on:
      - redis
      - ollama

  tts-processor:
    build: ./services/tts-processor
    restart: always
    depends_on:
      - redis

  bot-manager:
    build: ./services/bot-manager
    restart: always
    depends_on:
      - redis

volumes:
  redis_data:
```

### Kubernetes Deployment

```yaml
# k8s-deployment.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: hey-raven-stack
spec:
  replicas: 3
  selector:
    matchLabels:
      app: hey-raven
  template:
    metadata:
      labels:
        app: hey-raven
    spec:
      containers:
      - name: transcription-collector
        image: hey-raven/transcription-collector:latest
        env:
        - name: REDIS_HOST
          value: "redis-service"
```

### Load Balancing

For high-traffic deployments:

1. Use multiple LLM processor instances
2. Implement Redis Cluster for scaling
3. Load balance TTS requests
4. Use CDN for audio delivery

### Security

1. Enable Redis authentication
2. Use TLS for external connections
3. Implement API rate limiting
4. Regular security updates

## 📊 Performance Benchmarks

### Target Metrics

- **Wake word to response**: < 5 seconds
- **Concurrent sessions**: 100+
- **Uptime**: 99.9%
- **Memory usage**: < 2GB per service

### Load Testing

```bash
# Test wake word processing
python tests/load_test_wake_words.py --concurrent=10 --duration=60

# Test end-to-end workflow
python tests/load_test_full_workflow.py --sessions=50
```

## 📚 Additional Resources

- **API Documentation**: See `/docs/api/`
- **Architecture Guide**: See `/docs/architecture.md`
- **Contributing**: See `/CONTRIBUTING.md`
- **Troubleshooting**: See `/docs/troubleshooting.md`

## 🆘 Support

For issues and questions:

1. Check this deployment guide
2. Review logs and metrics
3. Run diagnostic scripts
4. Open GitHub issue with details

---

**🎉 Congratulations!** You now have a fully deployed Hey Raven voice assistant system with all advanced features enabled.


