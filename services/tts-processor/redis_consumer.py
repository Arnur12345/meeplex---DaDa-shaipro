"""
Redis stream consumer for TTS-Processor service.
Consumes llm_responses stream and publishes to tts_audio_queue stream.
"""
import logging
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any

import redis.asyncio as aioredis
import redis  # For redis.exceptions

from config import (
    REDIS_INPUT_STREAM_NAME,
    REDIS_OUTPUT_STREAM_NAME,
    REDIS_CONSUMER_GROUP,
    REDIS_STREAM_READ_COUNT,
    REDIS_STREAM_BLOCK_MS,
    CONSUMER_NAME,
    PENDING_MSG_TIMEOUT_MS
)
from tts_engine import TTSEngine
from audio_utils import encode_audio_to_base64

logger = logging.getLogger(__name__)

async def process_llm_response(
    message_id: str, 
    message_data: Dict[str, Any], 
    redis_c: aioredis.Redis,
    tts_engine: TTSEngine
) -> bool:
    """
    Process an LLM response message and generate TTS audio.
    
    Args:
        message_id: The Redis stream message ID
        message_data: The message data containing the LLM response
        redis_c: Redis client instance
        tts_engine: TTS engine instance
    
    Returns:
        True if processing is complete (can be ACKed), False if should retry
    """
    try:
        # Parse the payload
        payload_json = message_data.get('payload', '{}')
        if isinstance(payload_json, bytes):
            payload_json = payload_json.decode('utf-8')
        
        try:
            response_data = json.loads(payload_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON payload for message {message_id}: {e}. Payload: {payload_json[:200]}...")
            return True  # Bad data, ACK to avoid loop
        
        # Validate required fields
        required_fields = ["response", "session_uid", "meeting_id", "original_question"]
        if not all(field in response_data for field in required_fields):
            logger.warning(f"LLM response message {message_id} missing required fields. Required: {required_fields}. Data: {response_data}")
            return True  # Bad data, ACK to avoid loop
        
        response_text = response_data["response"]
        session_uid = response_data["session_uid"]
        meeting_id = response_data["meeting_id"]
        original_question = response_data["original_question"]
        original_timestamp = response_data.get("timestamp")
        
        logger.info(f"Processing LLM response {message_id}: '{response_text[:50]}...' for meeting {meeting_id}")
        
        # Generate TTS audio
        tts_result = await tts_engine.generate_speech_async(
            text=response_text,
            language=response_data.get("language", "en")
        )
        
        if tts_result is None:
            logger.error(f"Failed to generate TTS audio for message {message_id}")
            return False  # Retry the message
        
        audio_data, audio_metadata = tts_result
        
        # Encode audio for Redis streaming
        try:
            encoded_audio = encode_audio_to_base64(audio_data)
        except Exception as e:
            logger.error(f"Failed to encode audio for message {message_id}: {e}")
            return False  # Retry the message
        
        # Create TTS response message
        tts_response_data = {
            "audio_data": encoded_audio,
            "audio_metadata": audio_metadata,
            "session_uid": session_uid,
            "meeting_id": meeting_id,
            "original_question": original_question,
            "response_text": response_text,
            "audio_format": audio_metadata.get("format", "mp3"),
            "audio_duration": audio_metadata.get("duration_seconds"),
            "audio_size": audio_metadata.get("size_bytes"),
            "tts_engine": audio_metadata.get("engine"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_timestamp": original_timestamp,
            "message_id": str(uuid.uuid4())
        }
        
        # Publish to tts_audio_queue stream
        try:
            stream_message = {
                "payload": json.dumps(tts_response_data)
            }
            
            tts_message_id = await redis_c.xadd(
                REDIS_OUTPUT_STREAM_NAME,
                stream_message
            )
            
            logger.info(f"Published TTS audio {tts_message_id} to {REDIS_OUTPUT_STREAM_NAME} for LLM response {message_id}")
            logger.debug(f"Audio metadata: {audio_metadata}")
            
        except redis.exceptions.RedisError as e:
            logger.error(f"Failed to publish TTS audio to Redis stream for message {message_id}: {e}")
            return False  # Retry the message
        
        return True  # Successfully processed, can ACK
        
    except Exception as e:
        logger.error(f"Unexpected error processing LLM response {message_id}: {e}", exc_info=True)
        return False  # Retry the message

async def claim_stale_messages(redis_c: aioredis.Redis, tts_engine: TTSEngine):
    """Claims and processes stale messages from the Redis Stream for the current consumer."""
    messages_claimed_total = 0
    processed_claim_count = 0
    acked_claim_count = 0
    error_claim_count = 0

    logger.info(f"Starting stale message check (consumer: {CONSUMER_NAME}, idle > {PENDING_MSG_TIMEOUT_MS}ms).")

    try:
        while True:
            pending_details = await redis_c.xpending_range(
                name=REDIS_INPUT_STREAM_NAME,
                groupname=REDIS_CONSUMER_GROUP,
                min='-',
                max='+',
                count=100 
            )

            if not pending_details:
                logger.debug("No more pending messages found for the group during stale check.")
                break

            stale_candidates = [
                msg for msg in pending_details
                if msg.get('idle', 0) > PENDING_MSG_TIMEOUT_MS
            ]

            if not stale_candidates:
                logger.debug("No messages found exceeding idle time in the current pending batch.")
                if len(pending_details) < 100:
                    break 
                else:
                    logger.debug("Checked 100 pending messages, none were stale enough. More might exist but stopping check for this run.")
                    break
            
            stale_message_ids = [msg['message_id'] for msg in stale_candidates]
            logger.info(f"Found {len(stale_message_ids)} potentially stale message(s) to claim: {stale_message_ids}")

            if stale_message_ids:
                claimed_messages = await redis_c.xclaim(
                    name=REDIS_INPUT_STREAM_NAME,
                    groupname=REDIS_CONSUMER_GROUP,
                    consumername=CONSUMER_NAME,
                    min_idle_time=PENDING_MSG_TIMEOUT_MS, 
                    message_ids=stale_message_ids,
                )
                
                messages_claimed_now = len(claimed_messages)
                messages_claimed_total += messages_claimed_now
                if messages_claimed_now > 0:
                    logger.info(f"Successfully claimed {messages_claimed_now} stale message(s): {[msg[0].decode('utf-8') for msg in claimed_messages]}")

                for message_id_bytes, message_data_bytes in claimed_messages:
                    message_id_str = message_id_bytes.decode('utf-8') if isinstance(message_id_bytes, bytes) else message_id_bytes
                    message_data_decoded: Dict[str, Any] = {}
                    if isinstance(message_data_bytes, dict):
                        # Already decoded
                        message_data_decoded = {k: v for k, v in message_data_bytes.items()}
                    else:
                        # Need to decode
                        message_data_decoded = {k.decode('utf-8'): v.decode('utf-8') for k, v in message_data_bytes.items()}
                    
                    logger.info(f"Processing claimed stale message {message_id_str}...")
                    processed_claim_count += 1
                    try:
                        success = await process_llm_response(message_id_str, message_data_decoded, redis_c, tts_engine)
                        if success:
                            logger.info(f"Successfully processed claimed stale message {message_id_str}. Acknowledging.")
                            await redis_c.xack(REDIS_INPUT_STREAM_NAME, REDIS_CONSUMER_GROUP, message_id_str)
                            acked_claim_count += 1
                        else:
                            logger.warning(f"Processing failed for claimed stale message {message_id_str}. Not acknowledging.")
                            error_claim_count += 1
                    except Exception as e:
                        logger.error(f"Error processing claimed stale message {message_id_str}: {e}", exc_info=True)
                        error_claim_count += 1
            
            if not stale_candidates or len(pending_details) < 100:
                break

    except redis.exceptions.RedisError as e:
        logger.error(f"Redis error during stale message claiming: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Unexpected error during stale message claiming: {e}", exc_info=True)

    logger.info(f"Stale message check finished. Total claimed: {messages_claimed_total}, Processed: {processed_claim_count}, Acked: {acked_claim_count}, Errors: {error_claim_count}")

async def consume_llm_responses(redis_c: aioredis.Redis, tts_engine: TTSEngine):
    """Background task to consume LLM responses from Redis Stream."""
    last_processed_id = '>' 
    logger.info(f"Starting LLM response consumer loop for '{CONSUMER_NAME}', reading new messages ('>')...")

    while True:
        try:
            response = await redis_c.xreadgroup(
                groupname=REDIS_CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={REDIS_INPUT_STREAM_NAME: last_processed_id},
                count=REDIS_STREAM_READ_COUNT,
                block=REDIS_STREAM_BLOCK_MS 
            )

            if not response:
                continue

            for stream_name_bytes, messages in response:
                message_ids_to_ack = []
                processed_count = 0
                
                for message_id_bytes, message_data_bytes in messages:
                    message_id_str = message_id_bytes.decode('utf-8') if isinstance(message_id_bytes, bytes) else message_id_bytes
                    message_data_decoded: Dict[str, Any] = {}
                    if isinstance(message_data_bytes, dict):
                        # Already decoded
                        message_data_decoded = {k: v for k, v in message_data_bytes.items()}
                    else:
                        # Need to decode
                        message_data_decoded = {k.decode('utf-8'): v.decode('utf-8') for k, v in message_data_bytes.items()}
                    
                    should_ack = False
                    processed_count += 1
                    try:
                        should_ack = await process_llm_response(message_id_str, message_data_decoded, redis_c, tts_engine)
                    except Exception as e:
                        logger.error(f"Critical error during process_llm_response call for {message_id_str}: {e}", exc_info=True)
                        should_ack = False
                    
                    if should_ack:
                        message_ids_to_ack.append(message_id_str)
                        
                if message_ids_to_ack:
                    try:
                        await redis_c.xack(REDIS_INPUT_STREAM_NAME, REDIS_CONSUMER_GROUP, *message_ids_to_ack)
                        logger.debug(f"Acknowledged {len(message_ids_to_ack)}/{processed_count} messages: {message_ids_to_ack}")
                    except Exception as e:
                        logger.error(f"Failed to acknowledge messages {message_ids_to_ack}: {e}", exc_info=True)
        
        except asyncio.CancelledError:
            logger.info("LLM response consumer task cancelled.")
            break
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error in LLM response consumer: {e}. Retrying after delay...", exc_info=True)
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Unhandled error in LLM response consumer loop: {e}", exc_info=True)
            await asyncio.sleep(5)

async def initialize_redis_streams(redis_c: aioredis.Redis):
    """Initialize Redis streams and consumer groups for the TTS processor."""
    try:
        # Create consumer group for input stream (llm_responses)
        try:
            await redis_c.xgroup_create(
                REDIS_INPUT_STREAM_NAME, 
                REDIS_CONSUMER_GROUP, 
                id='0', 
                mkstream=True
            )
            logger.info(f"Created consumer group '{REDIS_CONSUMER_GROUP}' for stream '{REDIS_INPUT_STREAM_NAME}'")
        except redis.exceptions.ResponseError as e:
            if "BUSYGROUP" in str(e):
                logger.info(f"Consumer group '{REDIS_CONSUMER_GROUP}' already exists for stream '{REDIS_INPUT_STREAM_NAME}'")
            else:
                raise
        
        # Ensure output stream exists by adding a dummy message and deleting it
        try:
            dummy_msg_id = await redis_c.xadd(REDIS_OUTPUT_STREAM_NAME, {"dummy": "init"})
            await redis_c.xdel(REDIS_OUTPUT_STREAM_NAME, dummy_msg_id)
            logger.info(f"Ensured output stream '{REDIS_OUTPUT_STREAM_NAME}' exists")
        except Exception as e:
            logger.warning(f"Could not initialize output stream: {e}")
        
        logger.info("Redis streams initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize Redis streams: {e}", exc_info=True)
        raise
