"""
TTS-Processor FastAPI service.
Consumes LLM responses and generates TTS audio for streaming.
"""
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
    HEALTH_CHECK_INTERVAL,
    log_configuration
)
from tts_engine import TTSEngine
from redis_consumer import (
    consume_llm_responses, 
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
tts_engine: TTSEngine = None
consumer_task: asyncio.Task = None
stale_message_task: asyncio.Task = None

class GenerateRequest(BaseModel):
    text: str
    language: str = "en"
    voice_options: Dict[str, Any] = {}

class GenerateResponse(BaseModel):
    audio_data: str  # Base64 encoded
    audio_metadata: Dict[str, Any]
    status: str = "success"

class HealthResponse(BaseModel):
    status: str
    tts_ready: bool
    redis_connected: bool
    engine_status: Dict[str, Any]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifespan of the FastAPI application."""
    global redis_client, tts_engine, consumer_task, stale_message_task
    
    logger.info("Starting TTS-Processor service...")
    log_configuration()
    
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
        
        # Initialize TTS engine
        logger.info("Initializing TTS engine...")
        tts_engine = TTSEngine()
        
        if not tts_engine.engine_ready:
            logger.error("TTS engine initialization failed")
            raise RuntimeError("TTS engine initialization failed")
        
        logger.info("TTS engine initialized successfully")
        
        # Start background tasks
        consumer_task = asyncio.create_task(
            consume_llm_responses(redis_client, tts_engine),
            name="llm_response_consumer"
        )
        
        stale_message_task = asyncio.create_task(
            periodic_stale_message_cleanup(redis_client, tts_engine),
            name="stale_message_cleanup"
        )
        
        logger.info("Background tasks started")
        logger.info("TTS-Processor service startup completed")
        
        yield  # Application runs here
        
    except Exception as e:
        logger.error(f"Failed to start TTS-Processor service: {e}", exc_info=True)
        raise
    
    finally:
        # Cleanup on shutdown
        logger.info("Shutting down TTS-Processor service...")
        
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
        
        logger.info("TTS-Processor service shutdown completed")

async def periodic_stale_message_cleanup(redis_c: aioredis.Redis, tts_engine: TTSEngine):
    """Periodically claim and process stale messages."""
    while True:
        try:
            await asyncio.sleep(HEALTH_CHECK_INTERVAL)
            await claim_stale_messages(redis_c, tts_engine)
        except asyncio.CancelledError:
            logger.info("Stale message cleanup task cancelled")
            break
        except Exception as e:
            logger.error(f"Error in periodic stale message cleanup: {e}", exc_info=True)
            await asyncio.sleep(5)

# Create FastAPI application
app = FastAPI(
    title="TTS-Processor Service", 
    description="Text-to-Speech processor for LLM responses with Redis streaming",
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
    tts_ready = False
    engine_status = {}
    
    try:
        # Check Redis connection
        if redis_client:
            await redis_client.ping()
            redis_connected = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
    
    try:
        # Check TTS engine health
        if tts_engine:
            tts_ready = await tts_engine.health_check()
            engine_status = tts_engine.get_engine_status()
    except Exception as e:
        logger.warning(f"TTS health check failed: {e}")
    
    status = "healthy" if redis_connected and tts_ready else "unhealthy"
    
    return HealthResponse(
        status=status,
        tts_ready=tts_ready,
        redis_connected=redis_connected,
        engine_status=engine_status
    )

@app.get("/engines")
async def list_engines():
    """List available TTS engines and their status."""
    try:
        if not tts_engine:
            raise HTTPException(status_code=503, detail="TTS engine not initialized")
        
        return {
            "engines": tts_engine.list_available_engines(),
            "status": tts_engine.get_engine_status()
        }
    except Exception as e:
        logger.error(f"Error listing engines: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to list engines: {str(e)}")

@app.post("/generate", response_model=GenerateResponse)
async def generate_audio(request: GenerateRequest):
    """Generate TTS audio from text (for testing purposes)."""
    try:
        if not tts_engine or not tts_engine.engine_ready:
            raise HTTPException(status_code=503, detail="TTS engine is not ready")
        
        result = await tts_engine.generate_speech_async(
            text=request.text,
            language=request.language,
            voice_options=request.voice_options
        )
        
        if result is None:
            raise HTTPException(status_code=500, detail="Failed to generate audio")
        
        audio_data, audio_metadata = result
        
        # Encode audio for response
        from audio_utils import encode_audio_to_base64
        encoded_audio = encode_audio_to_base64(audio_data)
        
        return GenerateResponse(
            audio_data=encoded_audio,
            audio_metadata=audio_metadata
        )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating audio: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audio generation failed: {str(e)}")

@app.get("/stats")
async def get_stats():
    """Get TTS processing statistics."""
    try:
        if not tts_engine:
            raise HTTPException(status_code=503, detail="TTS engine not initialized")
        
        engine_status = tts_engine.get_engine_status()
        
        # Add stream information
        stream_info = {}
        if redis_client:
            try:
                # Get stream lengths
                input_length = await redis_client.xlen(redis_client.connection_pool.connection_kwargs.get('host', 'llm_responses'))
                output_length = await redis_client.xlen(redis_client.connection_pool.connection_kwargs.get('host', 'tts_audio_queue'))
                stream_info = {
                    "input_stream_length": input_length,
                    "output_stream_length": output_length
                }
            except Exception as e:
                logger.warning(f"Failed to get stream info: {e}")
                stream_info = {"error": "Could not retrieve stream information"}
        
        return {
            "engine_status": engine_status,
            "stream_info": stream_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint."""
    engine_info = {}
    if tts_engine:
        engine_info = {
            "preferred_engine": tts_engine.preferred_engine,
            "available_engines": tts_engine.list_available_engines()
        }
    
    return {
        "service": "TTS-Processor",
        "status": "running",
        "engine_info": engine_info,
        "endpoints": {
            "health": "/health",
            "engines": "/engines", 
            "generate": "/generate",
            "stats": "/stats"
        }
    }

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting TTS-Processor service on {FASTAPI_HOST}:{FASTAPI_PORT}")
    uvicorn.run(
        "main:app",
        host=FASTAPI_HOST,
        port=FASTAPI_PORT,
        log_level=LOG_LEVEL.lower(),
        reload=False
    )


