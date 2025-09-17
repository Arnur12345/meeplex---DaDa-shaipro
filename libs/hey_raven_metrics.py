#!/usr/bin/env python3
"""
Hey Raven Metrics Library
Shared metrics library for all Hey Raven services.
"""

import time
import json
import logging
import asyncio
from typing import Dict, Optional, Any
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

class HeyRavenMetrics:
    """Metrics client for Hey Raven services."""
    
    def __init__(self, service_name: str, redis_url: str = "redis://redis:6379/0"):
        self.service_name = service_name
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            self._initialized = True
            logger.info(f"✅ Metrics client initialized for {self.service_name}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize metrics client: {e}")
            # Don't fail the service if metrics are unavailable
            self._initialized = False

    async def _publish_metric(self, metric_name: str, value: float, 
                            metric_type: str = 'gauge', tags: Optional[Dict] = None,
                            session_id: Optional[str] = None, meeting_id: Optional[str] = None):
        """Publish a metric to Redis stream."""
        if not self._initialized or not self.redis_client:
            return  # Silently fail if metrics not available
            
        try:
            metric_data = {
                'timestamp': time.time(),
                'service': self.service_name,
                'metric_type': metric_type,
                'metric_name': metric_name,
                'value': value,
                'tags': tags or {},
                'session_id': session_id,
                'meeting_id': meeting_id
            }
            
            stream_message = {
                'payload': json.dumps(metric_data)
            }
            
            await self.redis_client.xadd('hey_raven_metrics', stream_message)
            
        except Exception as e:
            logger.warning(f"⚠️  Failed to publish metric {metric_name}: {e}")

    async def increment_counter(self, metric_name: str, value: float = 1.0, 
                              tags: Optional[Dict] = None, session_id: Optional[str] = None):
        """Increment a counter metric."""
        await self._publish_metric(metric_name, value, 'counter', tags, session_id)

    async def set_gauge(self, metric_name: str, value: float, 
                       tags: Optional[Dict] = None, session_id: Optional[str] = None):
        """Set a gauge metric."""
        await self._publish_metric(metric_name, value, 'gauge', tags, session_id)

    async def record_timing(self, metric_name: str, duration_ms: float,
                           tags: Optional[Dict] = None, session_id: Optional[str] = None):
        """Record a timing metric."""
        await self._publish_metric(metric_name, duration_ms, 'timing', tags, session_id)

    async def record_error(self, error_type: str, error_message: str,
                          session_id: Optional[str] = None, meeting_id: Optional[str] = None):
        """Record an error metric."""
        tags = {
            'error_type': error_type,
            'error_message': error_message[:200]  # Truncate long messages
        }
        await self._publish_metric('error_occurred', 1.0, 'counter', tags, session_id, meeting_id)

    @asynccontextmanager
    async def timer(self, metric_name: str, tags: Optional[Dict] = None, 
                   session_id: Optional[str] = None):
        """Context manager for timing operations."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            await self.record_timing(metric_name, duration_ms, tags, session_id)

    async def record_wake_word_detection(self, question: str, session_id: str, 
                                       detection_time_ms: float, meeting_id: Optional[str] = None):
        """Record wake word detection metrics."""
        tags = {
            'question_length': str(len(question)),
            'has_question': str(bool(question.strip()))
        }
        
        await self.increment_counter('wake_word_detected', 1.0, tags, session_id)
        await self.record_timing('wake_word_detection_time', detection_time_ms, tags, session_id)

    async def record_llm_processing(self, question: str, response: str, 
                                  processing_time_ms: float, session_id: str,
                                  meeting_id: Optional[str] = None, success: bool = True):
        """Record LLM processing metrics."""
        tags = {
            'question_length': str(len(question)),
            'response_length': str(len(response)),
            'success': str(success)
        }
        
        if success:
            await self.increment_counter('llm_requests_successful', 1.0, tags, session_id)
        else:
            await self.increment_counter('llm_requests_failed', 1.0, tags, session_id)
            
        await self.record_timing('llm_processing_time', processing_time_ms, tags, session_id)

    async def record_tts_generation(self, text: str, audio_duration_seconds: float,
                                  generation_time_ms: float, session_id: str,
                                  audio_format: str = 'mp3', success: bool = True):
        """Record TTS generation metrics."""
        tags = {
            'text_length': str(len(text)),
            'audio_duration': str(audio_duration_seconds),
            'audio_format': audio_format,
            'success': str(success)
        }
        
        if success:
            await self.increment_counter('tts_requests_successful', 1.0, tags, session_id)
        else:
            await self.increment_counter('tts_requests_failed', 1.0, tags, session_id)
            
        await self.record_timing('tts_generation_time', generation_time_ms, tags, session_id)

    async def record_audio_playback(self, audio_id: str, playback_duration_ms: float,
                                  session_id: str, success: bool = True):
        """Record audio playback metrics."""
        tags = {
            'audio_id': audio_id,
            'success': str(success)
        }
        
        if success:
            await self.increment_counter('audio_playback_successful', 1.0, tags, session_id)
        else:
            await self.increment_counter('audio_playback_failed', 1.0, tags, session_id)
            
        await self.record_timing('audio_playback_time', playback_duration_ms, tags, session_id)

    async def record_end_to_end_request(self, session_id: str, total_time_ms: float,
                                      question: str, response: str, success: bool = True):
        """Record complete end-to-end request metrics."""
        tags = {
            'question_length': str(len(question)),
            'response_length': str(len(response)),
            'success': str(success)
        }
        
        if success:
            await self.increment_counter('end_to_end_requests_successful', 1.0, tags, session_id)
        else:
            await self.increment_counter('end_to_end_requests_failed', 1.0, tags, session_id)
            
        await self.record_timing('end_to_end_response_time', total_time_ms, tags, session_id)
        
        # Record if we met the 5-second target
        target_met = total_time_ms <= 5000
        await self.increment_counter('target_response_time_met' if target_met else 'target_response_time_missed', 
                                   1.0, tags, session_id)

    async def record_service_health(self, health_status: str, additional_info: Optional[Dict] = None):
        """Record service health status."""
        tags = {'health_status': health_status}
        if additional_info:
            tags.update(additional_info)
            
        await self.set_gauge('service_health', 1.0 if health_status == 'healthy' else 0.0, tags)

    async def record_session_start(self, session_id: str, meeting_id: Optional[str] = None):
        """Record session start."""
        tags = {'meeting_id': meeting_id} if meeting_id else {}
        await self.increment_counter('session_started', 1.0, tags, session_id)

    async def record_session_end(self, session_id: str, duration_seconds: float,
                               meeting_id: Optional[str] = None):
        """Record session end."""
        tags = {'meeting_id': meeting_id} if meeting_id else {}
        await self.increment_counter('session_ended', 1.0, tags, session_id)
        await self.record_timing('session_duration', duration_seconds * 1000, tags, session_id)

# Singleton instance for easy import
metrics_client: Optional[HeyRavenMetrics] = None

def get_metrics_client(service_name: str, redis_url: str = "redis://redis:6379/0") -> HeyRavenMetrics:
    """Get or create metrics client singleton."""
    global metrics_client
    if metrics_client is None or metrics_client.service_name != service_name:
        metrics_client = HeyRavenMetrics(service_name, redis_url)
    return metrics_client

async def initialize_metrics(service_name: str, redis_url: str = "redis://redis:6379/0"):
    """Initialize metrics client for a service."""
    client = get_metrics_client(service_name, redis_url)
    await client.initialize()
    return client


