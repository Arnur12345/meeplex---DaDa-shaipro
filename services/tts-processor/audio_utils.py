"""
Audio processing utilities for TTS-Processor service.
Handles audio encoding, format conversion, and streaming.
"""
import base64
import io
import logging
from typing import Optional
import asyncio

logger = logging.getLogger(__name__)

def encode_audio_to_base64(audio_data: bytes) -> str:
    """
    Encode audio data to base64 string for Redis streaming.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        Base64 encoded string
    """
    try:
        encoded = base64.b64encode(audio_data).decode('utf-8')
        logger.debug(f"Encoded audio data: {len(audio_data)} bytes -> {len(encoded)} chars")
        return encoded
    except Exception as e:
        logger.error(f"Failed to encode audio to base64: {e}")
        raise

def decode_audio_from_base64(encoded_data: str) -> bytes:
    """
    Decode base64 string back to audio bytes.
    
    Args:
        encoded_data: Base64 encoded audio string
        
    Returns:
        Raw audio bytes
    """
    try:
        decoded = base64.b64decode(encoded_data.encode('utf-8'))
        logger.debug(f"Decoded audio data: {len(encoded_data)} chars -> {len(decoded)} bytes")
        return decoded
    except Exception as e:
        logger.error(f"Failed to decode audio from base64: {e}")
        raise

def get_audio_duration(audio_data: bytes, format: str = "mp3") -> Optional[float]:
    """
    Estimate audio duration from audio data.
    
    Args:
        audio_data: Raw audio bytes
        format: Audio format (mp3, wav)
        
    Returns:
        Duration in seconds, or None if estimation fails
    """
    try:
        # For MP3: rough estimation based on bitrate
        # This is a simple estimation - for precise duration, would need audio library
        if format.lower() == "mp3":
            # Typical MP3 at 64kbps: ~8KB per second
            estimated_duration = len(audio_data) / 8000
            logger.debug(f"Estimated MP3 duration: {estimated_duration:.2f}s for {len(audio_data)} bytes")
            return round(estimated_duration, 2)
        
        # For other formats, return None (unknown)
        return None
        
    except Exception as e:
        logger.warning(f"Failed to estimate audio duration: {e}")
        return None

def validate_audio_data(audio_data: bytes, max_size: int = 5 * 1024 * 1024) -> bool:
    """
    Validate audio data before processing.
    
    Args:
        audio_data: Raw audio bytes
        max_size: Maximum allowed size in bytes (default 5MB)
        
    Returns:
        True if valid, False otherwise
    """
    try:
        if not audio_data:
            logger.warning("Audio data is empty")
            return False
            
        if len(audio_data) > max_size:
            logger.warning(f"Audio data too large: {len(audio_data)} bytes > {max_size} bytes")
            return False
            
        # Basic format validation for MP3
        if audio_data[:3] == b'ID3' or audio_data[:2] == b'\xff\xfb':
            logger.debug("Valid MP3 format detected")
            return True
            
        # Basic format validation for WAV
        if audio_data[:4] == b'RIFF' and audio_data[8:12] == b'WAVE':
            logger.debug("Valid WAV format detected")
            return True
            
        # If we can't detect format, assume it's valid
        logger.debug("Unknown audio format, assuming valid")
        return True
        
    except Exception as e:
        logger.error(f"Audio validation failed: {e}")
        return False

async def async_encode_audio(audio_data: bytes) -> str:
    """
    Async wrapper for audio encoding to avoid blocking.
    
    Args:
        audio_data: Raw audio bytes
        
    Returns:
        Base64 encoded string
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, encode_audio_to_base64, audio_data)

def create_audio_metadata(
    audio_data: bytes,
    text: str,
    format: str = "mp3",
    engine: str = "gtts"
) -> dict:
    """
    Create metadata for audio data.
    
    Args:
        audio_data: Raw audio bytes
        text: Original text that was converted to speech
        format: Audio format
        engine: TTS engine used
        
    Returns:
        Dictionary with audio metadata
    """
    return {
        "format": format,
        "size_bytes": len(audio_data),
        "duration_seconds": get_audio_duration(audio_data, format),
        "text_length": len(text),
        "engine": engine,
        "encoding": "base64"
    }

class AudioStreamBuffer:
    """
    Buffer for handling audio streaming in memory.
    """
    
    def __init__(self):
        self.buffer = io.BytesIO()
        
    def write(self, data: bytes) -> int:
        """Write data to buffer."""
        return self.buffer.write(data)
        
    def getvalue(self) -> bytes:
        """Get all data from buffer."""
        return self.buffer.getvalue()
        
    def clear(self):
        """Clear the buffer."""
        self.buffer.seek(0)
        self.buffer.truncate(0)
        
    def size(self) -> int:
        """Get current buffer size."""
        return len(self.buffer.getvalue())
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.buffer.close()
