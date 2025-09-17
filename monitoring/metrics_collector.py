#!/usr/bin/env python3
"""
Hey Raven Metrics Collector
Centralized metrics collection and monitoring for all services.
"""

import time
import json
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from collections import defaultdict, deque
import redis.asyncio as aioredis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MetricEvent:
    """Represents a metric event from any service."""
    timestamp: float
    service: str
    metric_type: str
    metric_name: str
    value: float
    tags: Dict[str, str]
    session_id: Optional[str] = None
    meeting_id: Optional[str] = None

@dataclass
class PerformanceMetrics:
    """Performance metrics for the Hey Raven workflow."""
    # Response times
    wake_word_detection_ms: float = 0.0
    llm_processing_ms: float = 0.0
    tts_generation_ms: float = 0.0
    audio_playback_ms: float = 0.0
    total_response_ms: float = 0.0
    
    # Success rates
    wake_word_accuracy: float = 0.0
    llm_success_rate: float = 0.0
    tts_success_rate: float = 0.0
    audio_success_rate: float = 0.0
    end_to_end_success_rate: float = 0.0
    
    # Volume metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    
    # Session metrics
    active_sessions: int = 0
    average_session_duration: float = 0.0

class MetricsCollector:
    """Collects and aggregates metrics from all Hey Raven services."""
    
    def __init__(self, redis_url: str = "redis://redis:6379/0"):
        self.redis_url = redis_url
        self.redis_client: Optional[aioredis.Redis] = None
        self.metrics_buffer: deque = deque(maxlen=10000)
        self.performance_metrics = PerformanceMetrics()
        self.session_tracking: Dict[str, Dict] = {}
        self.service_health: Dict[str, Dict] = {}
        
    async def initialize(self):
        """Initialize Redis connection and start monitoring."""
        try:
            self.redis_client = aioredis.from_url(self.redis_url)
            await self.redis_client.ping()
            logger.info("✅ Metrics collector connected to Redis")
            
            # Subscribe to metric streams
            await self._subscribe_to_metrics()
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize metrics collector: {e}")
            raise

    async def _subscribe_to_metrics(self):
        """Subscribe to various metric streams."""
        metric_streams = [
            "hey_raven_metrics",
            "performance_metrics", 
            "error_metrics",
            "session_metrics"
        ]
        
        tasks = []
        for stream in metric_streams:
            task = asyncio.create_task(self._monitor_stream(stream))
            tasks.append(task)
            
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _monitor_stream(self, stream_name: str):
        """Monitor a specific metrics stream."""
        logger.info(f"📊 Monitoring metrics stream: {stream_name}")
        
        try:
            while True:
                try:
                    # Read from stream
                    messages = await self.redis_client.xread(
                        {stream_name: '$'}, 
                        count=10, 
                        block=2000
                    )
                    
                    for stream, msgs in messages:
                        for msg_id, fields in msgs:
                            await self._process_metric_message(stream.decode(), fields)
                            
                except asyncio.CancelledError:
                    logger.info(f"📊 Metrics monitoring cancelled for {stream_name}")
                    break
                except Exception as e:
                    logger.error(f"❌ Error monitoring {stream_name}: {e}")
                    await asyncio.sleep(5)
                    
        except Exception as e:
            logger.error(f"❌ Fatal error in metrics monitoring for {stream_name}: {e}")

    async def _process_metric_message(self, stream: str, fields: Dict):
        """Process a metric message from Redis stream."""
        try:
            # Decode fields if needed
            decoded_fields = {}
            for key, value in fields.items():
                if isinstance(key, bytes):
                    key = key.decode('utf-8')
                if isinstance(value, bytes):
                    value = value.decode('utf-8')
                decoded_fields[key] = value
            
            # Parse metric data
            metric_data = json.loads(decoded_fields.get('payload', '{}'))
            
            # Create metric event
            metric_event = MetricEvent(
                timestamp=metric_data.get('timestamp', time.time()),
                service=metric_data.get('service', 'unknown'),
                metric_type=metric_data.get('metric_type', 'counter'),
                metric_name=metric_data.get('metric_name', 'unknown'),
                value=float(metric_data.get('value', 0)),
                tags=metric_data.get('tags', {}),
                session_id=metric_data.get('session_id'),
                meeting_id=metric_data.get('meeting_id')
            )
            
            # Process the metric
            await self._update_metrics(metric_event)
            
        except Exception as e:
            logger.error(f"❌ Error processing metric message: {e}")

    async def _update_metrics(self, metric: MetricEvent):
        """Update aggregated metrics with new data."""
        self.metrics_buffer.append(metric)
        
        # Update service health
        self.service_health[metric.service] = {
            'last_seen': metric.timestamp,
            'status': 'healthy'
        }
        
        # Update performance metrics based on metric type
        if metric.metric_name == 'wake_word_detection_time':
            self.performance_metrics.wake_word_detection_ms = metric.value
        elif metric.metric_name == 'llm_processing_time':
            self.performance_metrics.llm_processing_ms = metric.value
        elif metric.metric_name == 'tts_generation_time':
            self.performance_metrics.tts_generation_ms = metric.value
        elif metric.metric_name == 'audio_playback_time':
            self.performance_metrics.audio_playback_ms = metric.value
        elif metric.metric_name == 'end_to_end_response_time':
            self.performance_metrics.total_response_ms = metric.value
            
        # Track sessions
        if metric.session_id:
            if metric.session_id not in self.session_tracking:
                self.session_tracking[metric.session_id] = {
                    'start_time': metric.timestamp,
                    'last_activity': metric.timestamp,
                    'events': []
                }
            else:
                self.session_tracking[metric.session_id]['last_activity'] = metric.timestamp
                
            self.session_tracking[metric.session_id]['events'].append(metric)

    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get current performance summary."""
        # Calculate active sessions
        current_time = time.time()
        active_sessions = sum(
            1 for session in self.session_tracking.values()
            if current_time - session['last_activity'] < 300  # 5 minutes
        )
        
        self.performance_metrics.active_sessions = active_sessions
        
        # Calculate success rates (simplified)
        recent_metrics = [m for m in self.metrics_buffer if current_time - m.timestamp < 3600]  # Last hour
        
        total_requests = len([m for m in recent_metrics if m.metric_name == 'request_started'])
        successful_requests = len([m for m in recent_metrics if m.metric_name == 'request_completed'])
        
        if total_requests > 0:
            self.performance_metrics.end_to_end_success_rate = successful_requests / total_requests * 100
        
        return {
            'performance_metrics': asdict(self.performance_metrics),
            'service_health': self.service_health,
            'active_sessions': len(self.session_tracking),
            'total_metrics_collected': len(self.metrics_buffer),
            'last_updated': datetime.now(timezone.utc).isoformat()
        }

    async def publish_metric(self, service: str, metric_name: str, value: float, 
                           metric_type: str = 'gauge', tags: Optional[Dict] = None,
                           session_id: Optional[str] = None, meeting_id: Optional[str] = None):
        """Publish a metric to the metrics stream."""
        try:
            metric_data = {
                'timestamp': time.time(),
                'service': service,
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
            logger.error(f"❌ Failed to publish metric: {e}")

    async def start_monitoring(self):
        """Start the monitoring process."""
        logger.info("🚀 Starting Hey Raven metrics monitoring...")
        
        # Create monitoring tasks
        tasks = [
            asyncio.create_task(self._subscribe_to_metrics()),
            asyncio.create_task(self._periodic_health_check()),
            asyncio.create_task(self._periodic_cleanup())
        ]
        
        try:
            await asyncio.gather(*tasks)
        except KeyboardInterrupt:
            logger.info("📊 Metrics monitoring stopped")
        except Exception as e:
            logger.error(f"❌ Metrics monitoring error: {e}")

    async def _periodic_health_check(self):
        """Periodically check service health."""
        while True:
            try:
                current_time = time.time()
                
                # Mark services as unhealthy if no recent activity
                for service, health in self.service_health.items():
                    if current_time - health['last_seen'] > 300:  # 5 minutes
                        health['status'] = 'unhealthy'
                        logger.warning(f"⚠️  Service {service} appears unhealthy")
                
                await asyncio.sleep(60)  # Check every minute
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Health check error: {e}")
                await asyncio.sleep(60)

    async def _periodic_cleanup(self):
        """Periodically clean up old session data."""
        while True:
            try:
                current_time = time.time()
                
                # Remove old sessions (older than 24 hours)
                sessions_to_remove = [
                    session_id for session_id, session_data in self.session_tracking.items()
                    if current_time - session_data['last_activity'] > 86400
                ]
                
                for session_id in sessions_to_remove:
                    del self.session_tracking[session_id]
                
                if sessions_to_remove:
                    logger.info(f"🧹 Cleaned up {len(sessions_to_remove)} old sessions")
                
                await asyncio.sleep(3600)  # Clean up every hour
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Cleanup error: {e}")
                await asyncio.sleep(3600)

async def main():
    """Main function for running the metrics collector."""
    import os
    
    redis_url = os.getenv('REDIS_URL', 'redis://redis:6379/0')
    
    collector = MetricsCollector(redis_url)
    await collector.initialize()
    await collector.start_monitoring()

if __name__ == '__main__':
    asyncio.run(main())


