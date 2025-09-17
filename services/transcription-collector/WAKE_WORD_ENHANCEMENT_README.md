# Enhanced Wake Word Detection for RavenAI

## Overview

The enhanced wake word detection system provides advanced pattern recognition, fuzzy matching, rate limiting, and configuration management for "Hey, Raven" voice assistant interactions.

## Features

### 🎯 Advanced Pattern Recognition
- **15+ Wake Word Patterns** across multiple categories
- **Confidence Scoring** with pattern-type based thresholds
- **Fuzzy Matching** for ASR transcription error handling
- **Multi-language Support** ready (Spanish, French, German)

### ⚡ Performance & Reliability
- **Rate Limiting**: Prevents spam with 3-second cooldown and 15/minute limits
- **Session-based Tracking**: Per-session UID rate limiting
- **Best-match Selection**: Intelligent pattern prioritization
- **Memory Efficient**: Optimized pattern matching and timestamp cleanup

### ⚙️ Configuration Management
- **JSON Configuration**: Hot-reloadable `wake_word_config.json`
- **Environment Overrides**: Fine-tune via environment variables
- **Fallback Defaults**: Graceful degradation if config unavailable
- **Runtime Validation**: Pattern compilation and error handling

## Wake Word Patterns

### Primary Patterns (90% confidence)
```
"hey raven"
"hello raven"  
"hi raven"
```

### Secondary Patterns (70% confidence)
```
"okay raven"
"excuse me raven"
"raven"
"hey haven"  # Fuzzy match for ASR errors
"hello haven"  # Fuzzy match for ASR errors
```

### Conversational Patterns
```
"raven can you"
"raven could you"
"raven will you"
"raven would you"
"raven please"
"raven help me"
"raven tell me"
```

### Question Patterns
```
"raven what"
"raven where"
"raven when"
"raven who"
"raven why"
"raven how"
```

### Punctuation-based Patterns
```
"raven,"
"raven?"
```

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Wake Word Detection Configuration
WAKE_WORD_CONFIG_PATH=/app/config/wake_word_config.json
WAKE_WORD_SENSITIVITY=0.8
WAKE_WORD_DEBUG_MODE=false
WAKE_WORD_RATE_LIMIT_ENABLED=true
WAKE_WORD_FUZZY_MATCHING=true
WAKE_WORD_COOLDOWN_SECONDS=3
WAKE_WORD_MAX_PER_MINUTE=15
```

### Configuration File

The `config/wake_word_config.json` file allows detailed pattern management:

```json
{
  "patterns": {
    "primary": ["hey raven", "hello raven", "hi raven"],
    "secondary": ["okay raven", "excuse me raven", "raven"],
    "conversational": ["raven can you", "raven help me"],
    "question_patterns": ["raven what", "raven where"],
    "punctuation_based": ["raven,", "raven?"]
  },
  "sensitivity": {
    "primary_threshold": 0.9,
    "secondary_threshold": 0.7,
    "fuzzy_match_enabled": true,
    "min_question_length": 3,
    "max_question_length": 200
  },
  "rate_limiting": {
    "enabled": true,
    "cooldown_seconds": 3,
    "max_detections_per_minute": 15
  }
}
```

## Usage

### Makefile Commands

```bash
# Test wake word detection patterns
make wake-word-test

# View current configuration
make wake-word-config

# Monitor wake word detections in logs
make logs | grep 'WakeWord Detected'

# Monitor Redis streams
make llm-streams
```

### Testing Locally

Run the test script:

```bash
cd raven_api
python test_wake_word_enhancement.py
```

### Live Testing

1. Start the services:
   ```bash
   make up
   ```

2. Send audio with wake words through WhisperLive

3. Monitor detection logs:
   ```bash
   make logs | grep 'WakeWord Detected'
   ```

4. Check Redis streams:
   ```bash
   make llm-streams
   ```

## Rate Limiting

### How It Works
- **Cooldown Period**: 3 seconds between detections per session
- **Rate Limit**: Maximum 15 detections per minute per session
- **Session Tracking**: Uses session UID for isolation
- **Memory Management**: Automatic cleanup of old timestamps

### Configuration
```json
{
  "rate_limiting": {
    "enabled": true,
    "cooldown_seconds": 3,
    "max_detections_per_minute": 15,
    "per_speaker_limiting": true,
    "debounce_same_segment": true
  }
}
```

## Fuzzy Matching

### ASR Error Handling
Common transcription errors are automatically corrected:

```
"hey haven" → "hey raven"
"hello haven" → "hello raven"
"hi haven" → "hi raven"
```

### Configuration
```json
{
  "sensitivity": {
    "fuzzy_match_enabled": true,
    "fuzzy_distance_threshold": 2
  }
}
```

## Logging

### Wake Word Detection Logs
```
[WakeWord Detected] primary: 'hey raven' -> Question: 'what time is it?' (confidence: 0.90)
[WakeWord Detected] fuzzy: 'hey haven' -> Question: 'can you help me?' (confidence: 0.70)
```

### Rate Limiting Logs
```
Wake word detection rate limited for session abc123
```

### Configuration Logs
```
Loaded wake word configuration from /app/config/wake_word_config.json
Compiled 18 wake word patterns
```

## Integration

### Redis Streams
- **Input**: Transcription segments from WhisperLive
- **Output**: Wake word commands to `hey_raven_commands` stream
- **Processing**: LLM processor consumes commands and generates responses

### Message Format
```json
{
  "question": "what time is it?",
  "session_uid": "abc123",
  "meeting_id": 456,
  "context": "Meeting segment at 12.5s",
  "timestamp": "2025-01-16T10:30:00Z",
  "type": "wake_word_command"
}
```

## Performance Metrics

### Target Metrics
- **Accuracy**: >95% (improved from ~90%)
- **False Positive Rate**: <2% (improved from ~5%)
- **Response Time**: <100ms per segment
- **Memory Usage**: Optimized pattern compilation
- **Rate Limiting**: Effective spam prevention

### Monitoring
- Wake word detection count by pattern type
- Rate limiting effectiveness
- Question extraction quality
- Configuration reload success rate

## Troubleshooting

### Common Issues

1. **Configuration not loading**
   ```bash
   # Check file exists and is valid JSON
   docker compose exec transcription-collector cat /app/config/wake_word_config.json
   ```

2. **No wake word detections**
   ```bash
   # Check logs for pattern compilation
   make logs | grep "Compiled.*wake word patterns"
   
   # Test patterns manually
   python test_wake_word_enhancement.py
   ```

3. **Rate limiting too aggressive**
   ```bash
   # Adjust in .env file
   WAKE_WORD_COOLDOWN_SECONDS=1
   WAKE_WORD_MAX_PER_MINUTE=30
   ```

4. **Fuzzy matching not working**
   ```bash
   # Enable in .env
   WAKE_WORD_FUZZY_MATCHING=true
   ```

### Debug Mode
Enable detailed logging:
```bash
WAKE_WORD_DEBUG_MODE=true
```

## Migration Guide

### From Legacy System
The enhanced system is backward compatible:

1. **Existing function**: `detect_wake_word_and_extract_question(text)` still works
2. **New function**: `detect_wake_word_and_extract_question(text, session_uid)` adds rate limiting
3. **Configuration**: Defaults match previous behavior if no config file present

### Upgrading
1. Build new Docker image: `make build`
2. Update environment variables in `.env`
3. Restart services: `make up`
4. Test with: `make wake-word-test`

## Development

### Adding New Patterns
1. Edit `config/wake_word_config.json`
2. Add to appropriate category (primary, secondary, etc.)
3. Test with `python test_wake_word_enhancement.py`
4. Deploy changes

### Custom Configuration
1. Create custom config file
2. Set `WAKE_WORD_CONFIG_PATH` environment variable
3. Restart transcription-collector service

### Testing
- Unit tests: `python test_wake_word_enhancement.py`
- Integration tests: `make wake-word-test`
- Performance tests: Monitor logs during high traffic

## API Reference

### WakeWordDetector Class

```python
class WakeWordDetector:
    def __init__(self):
        """Initialize with configuration loading."""
        
    def detect_and_extract(self, text: str, session_uid: str = "") -> Optional[str]:
        """
        Enhanced wake word detection with rate limiting.
        
        Args:
            text: Transcribed text to analyze
            session_uid: Session UID for rate limiting
            
        Returns:
            Extracted question if wake word detected, None otherwise
        """
```

### Legacy Function

```python
def detect_wake_word_and_extract_question(text: str, session_uid: str = "") -> Optional[str]:
    """
    Backward-compatible function wrapper.
    
    Args:
        text: Transcribed text to analyze
        session_uid: Optional session UID for rate limiting
        
    Returns:
        Extracted question if wake word detected, None otherwise
    """
```

## Support

### Documentation
- Main docs: `raven_api/cursor-logs.md`
- Configuration: `config/wake_word_config.json`
- Testing: `test_wake_word_enhancement.py`

### Commands
- `make wake-word-config` - View current configuration
- `make wake-word-test` - Test detection patterns
- `make logs | grep WakeWord` - Monitor detections

### Performance
- Monitor Redis streams: `make llm-streams`
- Check service health: `make llm-health`
- View logs: `make logs`


