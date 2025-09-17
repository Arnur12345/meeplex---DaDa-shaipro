"""
Configuration management for TTS-Processor service.
"""
import os
import logging

logger = logging.getLogger(__name__)

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Redis Stream Configuration
REDIS_INPUT_STREAM_NAME = os.getenv("REDIS_INPUT_STREAM_NAME", "llm_responses")
REDIS_OUTPUT_STREAM_NAME = os.getenv("REDIS_OUTPUT_STREAM_NAME", "tts_audio_queue")
REDIS_CONSUMER_GROUP = os.getenv("REDIS_CONSUMER_GROUP", "tts_processor_group")

# Redis Consumer Settings
REDIS_STREAM_READ_COUNT = int(os.getenv("REDIS_STREAM_READ_COUNT", "10"))
REDIS_STREAM_BLOCK_MS = int(os.getenv("REDIS_STREAM_BLOCK_MS", "2000"))
CONSUMER_NAME = os.getenv("CONSUMER_NAME", f"tts-processor-{os.getpid()}")
PENDING_MSG_TIMEOUT_MS = int(os.getenv("PENDING_MSG_TIMEOUT_MS", "30000"))

# TTS Engine Configuration
TTS_ENGINE = os.getenv("TTS_ENGINE", "gtts")  # gtts, pyttsx3
TTS_LANGUAGE = os.getenv("TTS_LANGUAGE", "en")
TTS_SLOW_SPEECH = os.getenv("TTS_SLOW_SPEECH", "false").lower() == "true"
TTS_AUDIO_FORMAT = os.getenv("TTS_AUDIO_FORMAT", "mp3")

# Audio Processing Configuration
AUDIO_SAMPLE_RATE = int(os.getenv("AUDIO_SAMPLE_RATE", "22050"))
AUDIO_BITRATE = os.getenv("AUDIO_BITRATE", "64k")
MAX_AUDIO_DURATION = int(os.getenv("MAX_AUDIO_DURATION", "30"))  # seconds
MAX_TEXT_LENGTH = int(os.getenv("MAX_TEXT_LENGTH", "1000"))  # characters

# FastAPI Configuration
FASTAPI_HOST = os.getenv("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.getenv("FASTAPI_PORT", "8000"))

# Service Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
HEALTH_CHECK_INTERVAL = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))

# TTS Performance Settings
TTS_TIMEOUT = int(os.getenv("TTS_TIMEOUT", "10"))  # seconds
TTS_RETRY_ATTEMPTS = int(os.getenv("TTS_RETRY_ATTEMPTS", "3"))
TTS_RETRY_DELAY = float(os.getenv("TTS_RETRY_DELAY", "1.0"))  # seconds

# Audio Encoding Settings
AUDIO_ENCODING = os.getenv("AUDIO_ENCODING", "base64")
AUDIO_COMPRESSION = os.getenv("AUDIO_COMPRESSION", "none")  # none, gzip

def log_configuration():
    """Log the current configuration for debugging."""
    logger.info("TTS-Processor Configuration:")
    logger.info(f"  Redis: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
    logger.info(f"  Input Stream: {REDIS_INPUT_STREAM_NAME}")
    logger.info(f"  Output Stream: {REDIS_OUTPUT_STREAM_NAME}")
    logger.info(f"  Consumer Group: {REDIS_CONSUMER_GROUP}")
    logger.info(f"  Consumer Name: {CONSUMER_NAME}")
    logger.info(f"  TTS Engine: {TTS_ENGINE}")
    logger.info(f"  Language: {TTS_LANGUAGE}")
    logger.info(f"  Audio Format: {TTS_AUDIO_FORMAT}")
    logger.info(f"  FastAPI: {FASTAPI_HOST}:{FASTAPI_PORT}")
    logger.info(f"  Log Level: {LOG_LEVEL}")


