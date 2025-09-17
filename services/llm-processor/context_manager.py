#!/usr/bin/env python3
"""
Context Manager for Hey Raven LLM Processor
Manages meeting context, conversation history, and personalized responses.
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

@dataclass
class ConversationTurn:
    """Represents a single conversation turn."""
    timestamp: str
    question: str
    response: str
    session_uid: str
    meeting_id: str
    context: str = ""

@dataclass
class MeetingContext:
    """Represents meeting context information."""
    meeting_id: str
    participants: List[str]
    topic: Optional[str] = None
    agenda_items: List[str] = None
    start_time: Optional[str] = None
    duration_minutes: Optional[int] = None
    key_points: List[str] = None
    action_items: List[str] = None

@dataclass
class SessionContext:
    """Represents session-specific context."""
    session_uid: str
    meeting_id: str
    conversation_history: List[ConversationTurn]
    user_preferences: Dict[str, Any]
    last_activity: str

class ContextManager:
    """Manages context for enhanced LLM responses."""
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
        self.context_cache: Dict[str, SessionContext] = {}
        self.meeting_cache: Dict[str, MeetingContext] = {}
        
    async def get_session_context(self, session_uid: str, meeting_id: str) -> SessionContext:
        """Get or create session context."""
        if session_uid in self.context_cache:
            return self.context_cache[session_uid]
            
        # Try to load from Redis
        try:
            context_key = f"session_context:{session_uid}"
            context_data = await self.redis.get(context_key)
            
            if context_data:
                data = json.loads(context_data)
                session_context = SessionContext(
                    session_uid=data['session_uid'],
                    meeting_id=data['meeting_id'],
                    conversation_history=[
                        ConversationTurn(**turn) for turn in data.get('conversation_history', [])
                    ],
                    user_preferences=data.get('user_preferences', {}),
                    last_activity=data.get('last_activity', datetime.now(timezone.utc).isoformat())
                )
            else:
                # Create new session context
                session_context = SessionContext(
                    session_uid=session_uid,
                    meeting_id=meeting_id,
                    conversation_history=[],
                    user_preferences={},
                    last_activity=datetime.now(timezone.utc).isoformat()
                )
                
            self.context_cache[session_uid] = session_context
            return session_context
            
        except Exception as e:
            logger.error(f"Error loading session context: {e}")
            # Return minimal context on error
            return SessionContext(
                session_uid=session_uid,
                meeting_id=meeting_id,
                conversation_history=[],
                user_preferences={},
                last_activity=datetime.now(timezone.utc).isoformat()
            )

    async def save_session_context(self, session_context: SessionContext):
        """Save session context to Redis."""
        try:
            context_key = f"session_context:{session_context.session_uid}"
            
            # Convert to serializable format
            data = {
                'session_uid': session_context.session_uid,
                'meeting_id': session_context.meeting_id,
                'conversation_history': [asdict(turn) for turn in session_context.conversation_history],
                'user_preferences': session_context.user_preferences,
                'last_activity': session_context.last_activity
            }
            
            # Save with 24-hour expiry
            await self.redis.setex(context_key, 86400, json.dumps(data))
            
            # Update cache
            self.context_cache[session_context.session_uid] = session_context
            
        except Exception as e:
            logger.error(f"Error saving session context: {e}")

    async def get_meeting_context(self, meeting_id: str) -> Optional[MeetingContext]:
        """Get meeting context information."""
        if meeting_id in self.meeting_cache:
            return self.meeting_cache[meeting_id]
            
        try:
            context_key = f"meeting_context:{meeting_id}"
            context_data = await self.redis.get(context_key)
            
            if context_data:
                data = json.loads(context_data)
                meeting_context = MeetingContext(**data)
                self.meeting_cache[meeting_id] = meeting_context
                return meeting_context
                
        except Exception as e:
            logger.error(f"Error loading meeting context: {e}")
            
        return None

    async def update_meeting_context(self, meeting_context: MeetingContext):
        """Update meeting context."""
        try:
            context_key = f"meeting_context:{meeting_context.meeting_id}"
            data = asdict(meeting_context)
            
            # Save with longer expiry (7 days)
            await self.redis.setex(context_key, 604800, json.dumps(data))
            
            # Update cache
            self.meeting_cache[meeting_context.meeting_id] = meeting_context
            
        except Exception as e:
            logger.error(f"Error saving meeting context: {e}")

    async def add_conversation_turn(self, session_uid: str, meeting_id: str,
                                 question: str, response: str, context: str = ""):
        """Add a conversation turn to history."""
        session_context = await self.get_session_context(session_uid, meeting_id)
        
        turn = ConversationTurn(
            timestamp=datetime.now(timezone.utc).isoformat(),
            question=question,
            response=response,
            session_uid=session_uid,
            meeting_id=meeting_id,
            context=context
        )
        
        session_context.conversation_history.append(turn)
        session_context.last_activity = turn.timestamp
        
        # Keep only last 10 turns to manage memory
        if len(session_context.conversation_history) > 10:
            session_context.conversation_history = session_context.conversation_history[-10:]
            
        await self.save_session_context(session_context)

    def build_context_prompt(self, session_uid: str, meeting_id: str, current_question: str) -> str:
        """Build enhanced context prompt for LLM."""
        context_parts = []
        
        # Base personality
        context_parts.append(
            "You are Raven, a helpful AI assistant integrated into a meeting system. "
            "Provide concise, helpful responses to questions during meetings. "
            "Keep responses brief and relevant to the meeting context."
        )
        
        # Session context
        if session_uid in self.context_cache:
            session_context = self.context_cache[session_uid]
            
            # Add conversation history
            if session_context.conversation_history:
                context_parts.append("\nRecent conversation history:")
                for turn in session_context.conversation_history[-3:]:  # Last 3 turns
                    context_parts.append(f"Q: {turn.question}")
                    context_parts.append(f"A: {turn.response}")
                    
        # Meeting context
        if meeting_id in self.meeting_cache:
            meeting_context = self.meeting_cache[meeting_id]
            
            context_parts.append(f"\nMeeting context:")
            if meeting_context.topic:
                context_parts.append(f"Topic: {meeting_context.topic}")
            if meeting_context.participants:
                context_parts.append(f"Participants: {', '.join(meeting_context.participants)}")
            if meeting_context.agenda_items:
                context_parts.append(f"Agenda: {', '.join(meeting_context.agenda_items)}")
            if meeting_context.key_points:
                context_parts.append(f"Key points discussed: {', '.join(meeting_context.key_points)}")
                
        # Current question
        context_parts.append(f"\nCurrent question: {current_question}")
        context_parts.append("\nProvide a helpful, concise response:")
        
        return "\n".join(context_parts)

    async def extract_meeting_insights(self, session_uid: str, meeting_id: str) -> Dict[str, Any]:
        """Extract insights from conversation history."""
        insights = {
            'key_topics': [],
            'action_items': [],
            'questions_asked': [],
            'response_patterns': {},
            'engagement_level': 'medium'
        }
        
        if session_uid in self.context_cache:
            session_context = self.context_cache[session_uid]
            
            # Analyze conversation history
            questions = [turn.question for turn in session_context.conversation_history]
            responses = [turn.response for turn in session_context.conversation_history]
            
            insights['questions_asked'] = questions
            insights['total_interactions'] = len(session_context.conversation_history)
            
            # Simple keyword extraction for topics
            all_text = ' '.join(questions + responses).lower()
            common_keywords = [
                'weather', 'time', 'schedule', 'meeting', 'project', 'task', 
                'deadline', 'update', 'status', 'help', 'question', 'problem'
            ]
            
            insights['key_topics'] = [
                keyword for keyword in common_keywords 
                if keyword in all_text
            ]
            
            # Detect action items (simple pattern matching)
            action_patterns = ['need to', 'should', 'will', 'must', 'todo', 'action']
            for response in responses:
                for pattern in action_patterns:
                    if pattern in response.lower():
                        insights['action_items'].append(response)
                        break
                        
        return insights

    async def suggest_followup_questions(self, session_uid: str, meeting_id: str, 
                                       last_response: str) -> List[str]:
        """Suggest relevant follow-up questions."""
        suggestions = []
        
        # Context-based suggestions
        if 'weather' in last_response.lower():
            suggestions.extend([
                "What about tomorrow's weather?",
                "Should we plan for indoor activities?",
                "What's the weekly forecast?"
            ])
        elif 'time' in last_response.lower():
            suggestions.extend([
                "What's our next meeting?",
                "How much time do we have left?",
                "When is the deadline?"
            ])
        elif 'project' in last_response.lower() or 'task' in last_response.lower():
            suggestions.extend([
                "What's the project status?",
                "Who's responsible for this task?",
                "What are the next steps?"
            ])
        else:
            # Generic helpful suggestions
            suggestions.extend([
                "Can you provide more details?",
                "What should we focus on next?",
                "Any other questions?"
            ])
            
        return suggestions[:3]  # Return top 3 suggestions

    async def cleanup_old_contexts(self):
        """Clean up old session contexts."""
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            cutoff_iso = cutoff_time.isoformat()
            
            sessions_to_remove = []
            for session_uid, context in self.context_cache.items():
                if context.last_activity < cutoff_iso:
                    sessions_to_remove.append(session_uid)
                    
            for session_uid in sessions_to_remove:
                del self.context_cache[session_uid]
                # Also remove from Redis
                await self.redis.delete(f"session_context:{session_uid}")
                
            if sessions_to_remove:
                logger.info(f"Cleaned up {len(sessions_to_remove)} old session contexts")
                
        except Exception as e:
            logger.error(f"Error during context cleanup: {e}")

# Enhanced context-aware prompt building
def build_enhanced_prompt(base_prompt: str, context_prompt: str, question: str) -> str:
    """Build enhanced prompt with context."""
    return f"{context_prompt}\n\nQuestion: {question}\n\nResponse:"


