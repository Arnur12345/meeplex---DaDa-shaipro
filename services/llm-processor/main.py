import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

import redis.asyncio as aioredis
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import (
    REDIS_HOST, 
    REDIS_PORT, 
    REDIS_DB,
    FASTAPI_HOST, 
    FASTAPI_PORT,
    LOG_LEVEL,
    HEALTH_CHECK_INTERVAL
)
from llm_client import ollama_client
from redis_consumer import (
    consume_wake_word_commands, 
    claim_stale_messages, 
    initialize_redis_streams
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global variables for background tasks
redis_client: aioredis.Redis = None
consumer_task: asyncio.Task = None
stale_message_task: asyncio.Task = None

class GenerateRequest(BaseModel):
    question: str
    context: str = ""

class GenerateResponse(BaseModel):
    response: str
    status: str = "success"

class HealthResponse(BaseModel):
    status: str
    ollama_ready: bool
    redis_connected: bool
    model_name: str

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI application."""
    global redis_client, consumer_task, stale_message_task
    
    logger.info("Starting LLM-Processor service...")
    
    try:
        # Initialize Redis connection
        logger.info(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
        redis_client = aioredis.Redis(
            host=REDIS_HOST, 
            port=REDIS_PORT, 
            db=REDIS_DB,
            decode_responses=False  # Keep as bytes to match existing pattern
        )
        
        # Test Redis connection
        await redis_client.ping()
        logger.info("Redis connection established")
        
        # Initialize Redis streams
        await initialize_redis_streams(redis_client)
        
        # Initialize Ollama client
        success = await ollama_client.initialize()
        if not success:
            logger.error("Failed to initialize Ollama client")
            raise RuntimeError("Ollama initialization failed")
        
        logger.info("Ollama client initialized successfully")
        
        # Start background tasks
        consumer_task = asyncio.create_task(
            consume_wake_word_commands(redis_client),
            name="wake_word_consumer"
        )
        
        stale_message_task = asyncio.create_task(
            periodic_stale_message_cleanup(redis_client),
            name="stale_message_cleanup"
        )
        
        logger.info("Background tasks started")
        logger.info("LLM-Processor service startup completed")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Failed to start LLM-Processor service: {e}", exc_info=True)
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down LLM-Processor service...")
        
        # Cancel background tasks
        if consumer_task and not consumer_task.done():
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                logger.info("Consumer task cancelled")
        
        if stale_message_task and not stale_message_task.done():
            stale_message_task.cancel()
            try:
                await stale_message_task
            except asyncio.CancelledError:
                logger.info("Stale message cleanup task cancelled")
        
        # Close Redis connection
        if redis_client:
            await redis_client.close()
            logger.info("Redis connection closed")
        
        logger.info("LLM-Processor service shutdown completed")

async def periodic_stale_message_cleanup(redis_c: aioredis.Redis):
    """Periodically claim and process stale messages."""
    while True:
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            await claim_stale_messages(redis_c)
        except asyncio.CancelledError:
            logger.info("Stale message cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic stale message cleanup: {e}", exc_info=True)
            await asyncio.sleep(5)

# Create FastAPI application
app = FastAPI(
    title="LLM-Processor Service", 
    description="Ollama-based LLM processor for wake word commands",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure as needed for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    redis_connected = False
    ollama_ready = False
    
    try:
        # Check Redis connection
        if redis_client:
            await redis_client.ping()
            redis_connected = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
    
    try:
        # Check Ollama health
        ollama_ready = await ollama_client.check_health() and ollama_client.model_ready
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
    
    status = "healthy" if redis_connected and ollama_ready else "unhealthy"
    
    return HealthResponse(
        status=status,
        ollama_ready=ollama_ready,
        redis_connected=redis_connected,
        model_name=ollama_client.model
    )

@app.get("/models")
async def list_models():
    """List available models in Ollama."""
    try:
        models = await ollama_client.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error listing models: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")

@app.post("/generate", response_model=GenerateResponse)
async def generate_response(request: GenerateRequest):
    """Generate a response using the LLM (for testing purposes)."""
    try:
        if not ollama_client.model_ready:
            raise HTTPException(status_code=503, detail="LLM model is not ready")
        
        response = await ollama_client.generate_response(
            question=request.question,
            context=request.context if request.context else None
        )
        
        if response is None:
            raise HTTPException(status_code=500, detail="Failed to generate response")
        
        return GenerateResponse(response=response)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating response: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "LLM-Processor",
        "status": "running",
        "model": ollama_client.model,
        "endpoints": {
            "health": "/health",
            "models": "/models", 
            "generate": "/generate"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting LLM-Processor service on {FASTAPI_HOST}:{FASTAPI_PORT}")
    uvicorn.run(
        "main:app",
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        log_level=LOG_LEVEL.lower(),
        reload=False
    )
