"""
Adapted TTS engine for stream-based processing without file system dependency.
Optimized for speed and reliability in production service environment.
"""
import logging
import asyncio
import warnings
from typing import Optional, Tuple, Dict, Any
import time

from audio_utils import (
    validate_audio_data, 
    create_audio_metadata,
    AudioStreamBuffer
)
from config import (
    TTS_ENGINE,
    TTS_LANGUAGE,
    TTS_SLOW_SPEECH,
    TTS_TIMEOUT,
    TTS_RETRY_ATTEMPTS,
    TTS_RETRY_DELAY,
    MAX_TEXT_LENGTH
)

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore")

try:
    from gtts import gTTS
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False
    logging.warning("gTTS not available. Install with: pip install gtts")

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False
    logging.warning("pyttsx3 not available. Install with: pip install pyttsx3")

logger = logging.getLogger(__name__)

class TTSEngine:
    """
    Stream-based TTS engine optimized for Redis integration.
    No file system dependency, all processing in memory.
    """
    
    def __init__(self, preferred_engine: str = None):
        """
        Initialize TTS engine.
        
        Args:
            preferred_engine: Preferred TTS engine ("gtts", "pyttsx3")
        """
        self.preferred_engine = preferred_engine or TTS_ENGINE
        self.pyttsx3_engine = None
        self.engine_ready = False
        
        # Statistics
        self.stats = {
            "generations": 0,
            "successes": 0,
            "failures": 0,
            "gtts_uses": 0,
            "pyttsx3_uses": 0,
            "avg_duration": 0.0
        }
        
        # Initialize preferred engine
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize the preferred TTS engine."""
        logger.info(f"Initializing TTS engine: {self.preferred_engine}")
        
        # Skip heavy models entirely - focus on speed
        if self.preferred_engine == "pyttsx3" and PYTTSX3_AVAILABLE:
            try:
                self.pyttsx3_engine = pyttsx3.init()
                # Configure for faster speech
                self.pyttsx3_engine.setProperty('rate', 200)  # Faster speech rate
                logger.info("pyttsx3 engine initialized successfully!")
                self.engine_ready = True
                return
            except Exception as e:
                logger.error(f"Failed to initialize pyttsx3: {e}")
        
        if GTTS_AVAILABLE:
            logger.info("Using gTTS as primary TTS engine")
            self.engine_ready = True
        else:
            logger.error("No TTS engines available!")
    
    async def generate_speech_async(
        self, 
        text: str, 
        language: str = None,
        voice_options: Dict[str, Any] = None
    ) -> Optional[Tuple[bytes, Dict[str, Any]]]:
        """
        Generate speech from text asynchronously.
        
        Args:
            text: Text to convert to speech
            language: Language code (default from config)
            voice_options: Additional voice options
            
        Returns:
            Tuple of (audio_bytes, metadata) or None if failed
        """
        start_time = time.time()
        self.stats["generations"] += 1
        
        try:
            # Validate and clean text
            cleaned_text = self._validate_and_clean_text(text)
            if not cleaned_text:
                logger.warning(f"Text validation failed for: {text[:50]}...")
                return None
            
            language = language or TTS_LANGUAGE
            
            # Try primary engine first
            for attempt in range(TTS_RETRY_ATTEMPTS):
                try:
                    if self.preferred_engine == "gtts" and GTTS_AVAILABLE:
                        result = await self._generate_gtts_async(cleaned_text, language)
                        if result:
                            self.stats["gtts_uses"] += 1
                            break
                    
                    if self.preferred_engine == "pyttsx3" and self.pyttsx3_engine:
                        result = await self._generate_pyttsx3_async(cleaned_text)
                        if result:
                            self.stats["pyttsx3_uses"] += 1
                            break
                            
                except Exception as e:
                    logger.warning(f"TTS attempt {attempt + 1} failed: {e}")
                    if attempt < TTS_RETRY_ATTEMPTS - 1:
                        await asyncio.sleep(TTS_RETRY_DELAY)
                        continue
                    else:
                        result = None
                        break
            
            # Try fallback engine if primary failed
            if not result:
                logger.info("Trying fallback TTS engine...")
                if self.preferred_engine != "gtts" and GTTS_AVAILABLE:
                    result = await self._generate_gtts_async(cleaned_text, language)
                    if result:
                        self.stats["gtts_uses"] += 1
                elif self.preferred_engine != "pyttsx3" and self.pyttsx3_engine:
                    result = await self._generate_pyttsx3_async(cleaned_text)
                    if result:
                        self.stats["pyttsx3_uses"] += 1
            
            if result:
                audio_data, engine_used = result
                
                # Create metadata
                metadata = create_audio_metadata(
                    audio_data, 
                    cleaned_text, 
                    "mp3", 
                    engine_used
                )
                
                # Update statistics
                duration = time.time() - start_time
                self.stats["successes"] += 1
                self.stats["avg_duration"] = (
                    (self.stats["avg_duration"] * (self.stats["successes"] - 1) + duration) 
                    / self.stats["successes"]
                )
                
                logger.info(f"TTS generation successful: {len(cleaned_text)} chars -> {len(audio_data)} bytes in {duration:.2f}s")
                return audio_data, metadata
            else:
                self.stats["failures"] += 1
                logger.error("All TTS engines failed to generate speech")
                return None
                
        except Exception as e:
            self.stats["failures"] += 1
            logger.error(f"TTS generation failed: {e}", exc_info=True)
            return None
    
    async def _generate_gtts_async(self, text: str, language: str) -> Optional[Tuple[bytes, str]]:
        """Generate speech using gTTS asynchronously."""
        try:
            logger.debug("Generating speech with gTTS...")
            
            # Create gTTS object
            tts = gTTS(
                text=text, 
                lang=language, 
                slow=TTS_SLOW_SPEECH
            )
            
            # Use in-memory buffer instead of file
            with AudioStreamBuffer() as buffer:
                # Run gTTS save in executor to avoid blocking
                loop = asyncio.get_event_loop()
                await asyncio.wait_for(
                    loop.run_in_executor(None, tts.write_to_fp, buffer),
                    timeout=TTS_TIMEOUT
                )
                
                audio_data = buffer.getvalue()
                
                if validate_audio_data(audio_data):
                    logger.debug(f"gTTS generation successful: {len(audio_data)} bytes")
                    return audio_data, "gtts"
                else:
                    logger.error("gTTS generated invalid audio data")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"gTTS generation timeout after {TTS_TIMEOUT}s")
            return None
        except Exception as e:
            logger.error(f"gTTS generation failed: {e}")
            return None
    
    async def _generate_pyttsx3_async(self, text: str) -> Optional[Tuple[bytes, str]]:
        """Generate speech using pyttsx3 asynchronously."""
        try:
            logger.debug("Generating speech with pyttsx3...")
            
            # pyttsx3 is synchronous, so run in executor
            loop = asyncio.get_event_loop()
            
            def _pyttsx3_generate():
                with AudioStreamBuffer() as buffer:
                    # Save to buffer instead of file
                    self.pyttsx3_engine.save_to_file(text, buffer)
                    self.pyttsx3_engine.runAndWait()
                    return buffer.getvalue()
            
            audio_data = await asyncio.wait_for(
                loop.run_in_executor(None, _pyttsx3_generate),
                timeout=TTS_TIMEOUT
            )
            
            if audio_data and validate_audio_data(audio_data):
                logger.debug(f"pyttsx3 generation successful: {len(audio_data)} bytes")
                return audio_data, "pyttsx3"
            else:
                logger.error("pyttsx3 generated invalid audio data")
                return None
                
        except asyncio.TimeoutError:
            logger.error(f"pyttsx3 generation timeout after {TTS_TIMEOUT}s")
            return None
        except Exception as e:
            logger.error(f"pyttsx3 generation failed: {e}")
            return None
    
    def _validate_and_clean_text(self, text: str) -> Optional[str]:
        """Validate and clean text for TTS processing."""
        try:
            if not text or not isinstance(text, str):
                return None
            
            # Remove excessive whitespace
            cleaned = ' '.join(text.split())
            
            # Check length limits
            if len(cleaned) > MAX_TEXT_LENGTH:
                logger.warning(f"Text too long ({len(cleaned)} chars), truncating to {MAX_TEXT_LENGTH}")
                cleaned = cleaned[:MAX_TEXT_LENGTH].rsplit(' ', 1)[0] + "..."
            
            # Basic text validation
            if len(cleaned.strip()) < 1:
                return None
                
            return cleaned
            
        except Exception as e:
            logger.error(f"Text validation failed: {e}")
            return None
    
    def get_engine_status(self) -> Dict[str, Any]:
        """Get current engine status and statistics."""
        return {
            "preferred_engine": self.preferred_engine,
            "engine_ready": self.engine_ready,
            "gtts_available": GTTS_AVAILABLE,
            "pyttsx3_available": PYTTSX3_AVAILABLE and self.pyttsx3_engine is not None,
            "statistics": self.stats.copy(),
            "available_engines": self.list_available_engines()
        }
    
    def list_available_engines(self) -> list:
        """Return list of available TTS engines."""
        engines = []
        if GTTS_AVAILABLE:
            engines.append("gtts")
        if PYTTSX3_AVAILABLE:
            engines.append("pyttsx3")
        return engines
    
    async def health_check(self) -> bool:
        """Perform a health check by generating a short test audio."""
        try:
            test_text = "TTS health check"
            result = await self.generate_speech_async(test_text)
            return result is not None
        except Exception as e:
            logger.error(f"TTS health check failed: {e}")
            return False
