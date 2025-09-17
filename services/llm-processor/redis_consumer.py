import logging
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional

import redis.asyncio as aioredis
import redis  # For redis.exceptions

from config import (
    REDIS_HOST,
    REDIS_PORT,
    REDIS_DB,
    REDIS_INPUT_STREAM_NAME,
    REDIS_OUTPUT_STREAM_NAME,
    REDIS_CONSUMER_GROUP,
    REDIS_STREAM_READ_COUNT,
    REDIS_STREAM_BLOCK_MS,
    CONSUMER_NAME,
    PENDING_MSG_TIMEOUT_MS
)
from llm_client import ollama_client
from context_manager import ContextManager

logger = logging.getLogger(__name__)

# Global context manager instance
context_manager: Optional[ContextManager] = None

async def process_wake_word_command(message_id: str, message_data: Dict[str, Any], redis_c: aioredis.Redis) -> bool:
    """
    Process a wake word command message from the Redis stream with context awareness.
    
    Args:
        message_id: The Redis stream message ID
        message_data: The message data containing the wake word command
        redis_c: Redis client instance
    
    Returns:
        True if processing is complete (can be ACKed), False if should retry
    """
    global context_manager
    
    try:
        # Initialize context manager if needed
        if context_manager is None:
            context_manager = ContextManager(redis_c)
        
        # Parse the payload
        payload_json = message_data.get('payload', '{}')
        if isinstance(payload_json, bytes):
            payload_json = payload_json.decode('utf-8')
        
        # Debug logging to see what we're actually receiving
        logger.debug(f"Raw message_data for {message_id}: {message_data}")
        logger.debug(f"Payload JSON for {message_id}: {payload_json}")
        
        try:
            command_data = json.loads(payload_json)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON payload for message {message_id}: {e}. Payload: {payload_json[:200]}...")
            return True  # Bad data, ACK to avoid loop
        
        # Validate required fields
        required_fields = ["question", "session_uid", "meeting_id", "timestamp"]
        if not all(field in command_data for field in required_fields):
            logger.warning(f"Wake word command message {message_id} missing required fields. Required: {required_fields}. Data: {command_data}")
            return True  # Bad data, ACK to avoid loop
        
        question = command_data["question"]
        session_uid = command_data["session_uid"]
        meeting_id = str(command_data["meeting_id"])  # Ensure string type
        timestamp = command_data["timestamp"]
        context = command_data.get("context", "")
        
        logger.info(f"Processing wake word command {message_id}: '{question}' for meeting {meeting_id}")
        
        # Simple LLM generation - call /generate endpoint directly
        import aiohttp
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "question": question,
                    "context": "It is the meeting, answer detaily"
                }
                async with session.post('http://localhost:8000/generate', json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response = result.get("response", "I couldn't generate a response.")
                        logger.info(f"Generated response for {message_id}: {response[:50]}...")
                    else:
                        logger.error(f"LLM generation failed with status {resp.status}")
                        response = "I'm sorry, I couldn't process your request."
        except Exception as e:
            logger.error(f"Error calling /generate endpoint: {e}")
            response = "I'm experiencing technical difficulties."
        
        # Create response message for TTS stream
        response_data = {
            "response": response,
            "session_uid": session_uid,
            "meeting_id": str(meeting_id),  # Ensure consistent string type
            "original_question": question,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "original_timestamp": timestamp,
            "message_id": str(uuid.uuid4())
        }
        
        # Publish to llm_responses stream
        try:
            stream_message = {
                "payload": json.dumps(response_data)
            }
            
            response_message_id = await redis_c.xadd(
                REDIS_OUTPUT_STREAM_NAME,
                stream_message
            )
            
            logger.info(f"Published LLM response {response_message_id} to {REDIS_OUTPUT_STREAM_NAME} for command {message_id}")
            logger.debug(f"Response content: {response[:100]}...")
            
        except redis.exceptions.RedisError as e:
            logger.error(f"Failed to publish response to Redis stream for command {message_id}: {e}")
            return False  # Retry the message
        
        return True  # Successfully processed, can ACK
        
    except Exception as e:
        logger.error(f"Unexpected error processing wake word command {message_id}: {e}", exc_info=True)
        return False  # Retry the message

async def claim_stale_messages(redis_c: aioredis.Redis):
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
                        # Convert bytes keys and values to strings
                        for k, v in message_data_bytes.items():
                            key = k.decode('utf-8') if isinstance(k, bytes) else str(k)
                            value = v.decode('utf-8') if isinstance(v, bytes) else str(v)
                            message_data_decoded[key] = value
                    else:
                        # Fallback decode
                        message_data_decoded = {k.decode('utf-8'): v.decode('utf-8') for k, v in message_data_bytes.items()}
                    
                    logger.info(f"Processing claimed stale message {message_id_str}...")
                    processed_claim_count += 1
                    try:
                        success = await process_wake_word_command(message_id_str, message_data_decoded, redis_c)
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

async def consume_wake_word_commands(redis_c: aioredis.Redis):
    """Background task to consume wake word commands from Redis Stream."""
    last_processed_id = '>' 
    logger.info(f"Starting wake word command consumer loop for '{CONSUMER_NAME}', reading new messages ('>')...")

    while True:
        try:
            logger.debug(f"Attempting to read from group '{REDIS_CONSUMER_GROUP}' with consumer '{CONSUMER_NAME}'")
            response = await redis_c.xreadgroup(
                groupname=REDIS_CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={REDIS_INPUT_STREAM_NAME: last_processed_id},
                count=REDIS_STREAM_READ_COUNT,
                block=100  # 100ms for debug 
            )
            logger.debug(f"Received response from Redis: {len(response) if response else 0} streams")

            if not response:
                continue

            for stream_name_bytes, messages in response:
                message_ids_to_ack = []
                processed_count = 0
                
                for message_id_bytes, message_data_bytes in messages:
                    message_id_str = message_id_bytes.decode('utf-8') if isinstance(message_id_bytes, bytes) else message_id_bytes
                    logger.debug(f"Raw message data for {message_id_str}: {message_data_bytes} (type: {type(message_data_bytes)})")
                    
                    message_data_decoded: Dict[str, Any] = {}
                    if isinstance(message_data_bytes, dict):
                        # Convert bytes keys and values to strings
                        for k, v in message_data_bytes.items():
                            key = k.decode('utf-8') if isinstance(k, bytes) else str(k)
                            value = v.decode('utf-8') if isinstance(v, bytes) else str(v)
                            message_data_decoded[key] = value
                            logger.debug(f"Decoded key '{key}' = '{value}'")
                    else:
                        # Fallback decode
                        message_data_decoded = {k.decode('utf-8'): v.decode('utf-8') for k, v in message_data_bytes.items()}
                    
                    logger.debug(f"Final decoded data for {message_id_str}: {message_data_decoded}")
                    
                    should_ack = False
                    processed_count += 1
                    try:
                        should_ack = await process_wake_word_command(message_id_str, message_data_decoded, redis_c)
                    except Exception as e:
                        logger.error(f"Critical error during process_wake_word_command call for {message_id_str}: {e}", exc_info=True)
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
            logger.info("Wake word command consumer task cancelled.")
            break
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error in wake word consumer: {e}. Retrying after delay...", exc_info=True)
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Unhandled error in wake word consumer loop: {e}", exc_info=True)
            await asyncio.sleep(5)

async def initialize_redis_streams(redis_c: aioredis.Redis):
    """Initialize Redis streams and consumer groups for the LLM processor."""
    try:
        # Create consumer group for input stream (hey_raven_commands)
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
