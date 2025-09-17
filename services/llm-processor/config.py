import os

# Redis connection configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "redis")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))

# Redis Stream configuration for LLM-Processor
REDIS_INPUT_STREAM_NAME = os.environ.get("REDIS_INPUT_STREAM_NAME", "hey_raven_commands")
REDIS_OUTPUT_STREAM_NAME = os.environ.get("REDIS_OUTPUT_STREAM_NAME", "llm_responses")
REDIS_CONSUMER_GROUP = os.environ.get("REDIS_CONSUMER_GROUP", "llm_processor_group")
REDIS_STREAM_READ_COUNT = int(os.environ.get("REDIS_STREAM_READ_COUNT", "10"))
REDIS_STREAM_BLOCK_MS = int(os.environ.get("REDIS_STREAM_BLOCK_MS", "2000"))  # 2 seconds

# Consumer name configuration
CONSUMER_NAME = os.environ.get("POD_NAME", "llm-processor-main")
PENDING_MSG_TIMEOUT_MS = 60000  # 1 minute timeout for stale messages

# Ollama configuration
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "localhost")
OLLAMA_PORT = int(os.environ.get("OLLAMA_PORT", "11434"))
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "mistral:7b")
OLLAMA_API_TIMEOUT = int(os.environ.get("OLLAMA_API_TIMEOUT", "60"))  # seconds
OLLAMA_MAX_RETRIES = int(os.environ.get("OLLAMA_MAX_RETRIES", "3"))

# LLM Response configuration
MAX_RESPONSE_LENGTH = int(os.environ.get("MAX_RESPONSE_LENGTH", "500"))
RESPONSE_TEMPERATURE = float(os.environ.get("RESPONSE_TEMPERATURE", "0.7"))
RAVEN_PERSONALITY_PROMPT = os.environ.get("RAVEN_PERSONALITY_PROMPT", 
    "You are Raven, a helpful AI assistant integrated into a meeting system. "
    "Provide concise, helpful responses to questions during meetings. "
    "Keep responses brief and relevant to the meeting context.")

# FastAPI configuration
FASTAPI_HOST = os.environ.get("FASTAPI_HOST", "0.0.0.0")
FASTAPI_PORT = int(os.environ.get("FASTAPI_PORT", "8000"))

# Logging configuration
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()

# Health check configuration
HEALTH_CHECK_INTERVAL = int(os.environ.get("HEALTH_CHECK_INTERVAL", "30"))  # seconds
OLLAMA_HEALTH_ENDPOINT = "/api/tags"

# Model pull verbosity (reduce noise during model downloading)
MODEL_PULL_VERBOSE = os.environ.get("MODEL_PULL_VERBOSE", "false").lower() == "true"
MODEL_PULL_PROGRESS_INTERVAL = int(os.environ.get("MODEL_PULL_PROGRESS_INTERVAL", "10"))  # Log every Nth progress update
