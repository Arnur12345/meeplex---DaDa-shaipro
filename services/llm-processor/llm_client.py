import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
import aiohttp
from aiohttp import ClientTimeout, ClientSession

from config import (
    OLLAMA_HOST, 
    OLLAMA_PORT, 
    OLLAMA_MODEL, 
    OLLAMA_API_TIMEOUT,
    OLLAMA_MAX_RETRIES,
    MAX_RESPONSE_LENGTH,
    RESPONSE_TEMPERATURE,
    RAVEN_PERSONALITY_PROMPT,
    OLLAMA_HEALTH_ENDPOINT,
    MODEL_PULL_VERBOSE,
    MODEL_PULL_PROGRESS_INTERVAL
)
from language_manager import language_manager

logger = logging.getLogger(__name__)

class OllamaClient:
    """Async HTTP client for Ollama API communication with retry logic and model management."""
    
    def __init__(self):
        self.base_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"
        self.model = OLLAMA_MODEL
        self.timeout = ClientTimeout(total=OLLAMA_API_TIMEOUT)
        self.model_ready = False
    
    async def initialize(self) -> bool:
        """Initialize the Ollama client and ensure model is available."""
        try:
            logger.info(f"Initializing Ollama client for model: {self.model}")
            
            # Check if Ollama is running
            if not await self.check_health():
                logger.error("Ollama service is not healthy")
                return False
            
            # Check if model exists, if not pull it
            if not await self.is_model_available():
                logger.info(f"Model {self.model} not found, attempting to pull...")
                if not await self.pull_model():
                    logger.error(f"Failed to pull model {self.model}")
                    return False
            
            # Verify model is working with a test generation
            test_response = await self.generate_response("Hello", test_mode=True)
            if test_response:
                self.model_ready = True
                logger.info("Ollama client initialized successfully")
                return True
            else:
                logger.error("Model test generation failed")
                return False
                
        except Exception as e:
            logger.error(f"Error initializing Ollama client: {e}", exc_info=True)
            return False
    
    async def check_health(self) -> bool:
        """Check if Ollama service is healthy."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}{OLLAMA_HEALTH_ENDPOINT}") as response:
                    if response.status == 200:
                        logger.debug("Ollama health check passed")
                        return True
                    else:
                        logger.warning(f"Ollama health check failed with status: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models in Ollama."""
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(f"{self.base_url}/api/tags") as response:
                    if response.status == 200:
                        data = await response.json()
                        models = data.get("models", [])
                        logger.debug(f"Available models: {[m.get('name') for m in models]}")
                        return models
                    else:
                        logger.error(f"Failed to list models, status: {response.status}")
                        return []
        except Exception as e:
            logger.error(f"Error listing models: {e}", exc_info=True)
            return []
    
    async def is_model_available(self) -> bool:
        """Check if the specified model is available."""
        try:
            models = await self.list_models()
            for model in models:
                if model.get("name") == self.model:
                    logger.debug(f"Model {self.model} is available")
                    return True
            logger.info(f"Model {self.model} is not available")
            return False
        except Exception as e:
            logger.error(f"Error checking model availability: {e}", exc_info=True)
            return False
    
    async def pull_model(self) -> bool:
        """Pull the specified model from Ollama registry."""
        try:
            logger.info(f"Pulling model: {self.model}")
            payload = {"name": self.model}
            
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.post(
                    f"{self.base_url}/api/pull", 
                    json=payload,
                    timeout=ClientTimeout(total=600)  # 10 minutes for model pulling
                ) as response:
                    if response.status == 200:
                        # Stream the response to track progress with configurable verbosity
                        last_status = None
                        progress_count = 0
                        
                        async for line in response.content:
                            if line:
                                try:
                                    progress_data = json.loads(line.decode('utf-8'))
                                    current_status = progress_data.get("status")
                                    
                                    # Log status changes
                                    if current_status != last_status:
                                        logger.info(f"Model pull: {current_status}")
                                        last_status = current_status
                                    
                                    # Handle progress updates based on verbosity setting
                                    elif current_status in ["pulling manifest", "downloading"]:
                                        progress_count += 1
                                        if MODEL_PULL_VERBOSE:
                                            # Verbose mode: log every update
                                            logger.info(f"Model pull: {current_status} (progress update #{progress_count})")
                                        else:
                                            # Quiet mode: log every Nth update
                                            if progress_count % MODEL_PULL_PROGRESS_INTERVAL == 0:
                                                logger.info(f"Model pull: {current_status} (progress update #{progress_count})")
                                    
                                    if current_status == "success":
                                        logger.info(f"Successfully pulled model: {self.model}")
                                        return True
                                        
                                except json.JSONDecodeError:
                                    continue
                        return True
                    else:
                        logger.error(f"Failed to pull model, status: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error pulling model: {e}", exc_info=True)
            return False
    
    async def generate_response(self, question: str, context: Optional[str] = None, test_mode: bool = False) -> Optional[str]:
        """Generate a response using the Ollama model with multi-language support and retry logic."""
        if not self.model_ready and not test_mode:
            logger.error("Model is not ready for generation")
            return None
        
        # Construct the prompt with language awareness
        if test_mode:
            prompt = "Test prompt. Respond with 'Hello' only."
        else:
            # Detect language and build appropriate prompt
            detected_language, confidence = language_manager.detect_language(question)
            logger.info(f"Detected language: {detected_language} (confidence: {confidence:.2f})")
            
            # Use multilingual prompt if we have reasonable confidence
            if confidence > 0.3:
                prompt = language_manager.build_multilingual_prompt(question, context or "", detected_language)
            else:
                # Fallback to default English prompt
                prompt = f"{RAVEN_PERSONALITY_PROMPT}\n\nQuestion: {question}"
                if context:
                    prompt = f"{RAVEN_PERSONALITY_PROMPT}\n\nContext: {context}\n\nQuestion: {question}"
        
        for attempt in range(OLLAMA_MAX_RETRIES):
            try:
                # Create a new session for each attempt to avoid closed session issues
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    payload = {
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": RESPONSE_TEMPERATURE,
                            "num_predict": MAX_RESPONSE_LENGTH
                        }
                    }
                    
                    logger.debug(f"Generating response (attempt {attempt + 1}/{OLLAMA_MAX_RETRIES})")
                    
                    async with session.post(f"{self.base_url}/api/generate", json=payload) as response:
                        if response.status == 200:
                            data = await response.json()
                            generated_response = data.get("response", "").strip()
                            
                            if test_mode:
                                logger.debug("Test generation successful")
                                return generated_response
                            
                            # Validate and clean the response
                            if len(generated_response) > MAX_RESPONSE_LENGTH:
                                generated_response = generated_response[:MAX_RESPONSE_LENGTH] + "..."
                            
                            if generated_response:
                                logger.info(f"Generated response: {generated_response[:100]}...")
                                return generated_response
                            else:
                                logger.warning("Generated response is empty")
                                
                        else:
                            logger.error(f"Generation failed with status: {response.status}")
                        
            except asyncio.TimeoutError:
                logger.warning(f"Generation timeout on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Generation error on attempt {attempt + 1}: {e}", exc_info=True)
            
            if attempt < OLLAMA_MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"Failed to generate response after {OLLAMA_MAX_RETRIES} attempts")
        return None

# Global client instance
ollama_client = OllamaClient()
