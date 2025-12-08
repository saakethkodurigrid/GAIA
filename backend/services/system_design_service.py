"""
System Design service for managing interview sessions, evaluations, and chat.
Uses Redis for hot data (fast access) and PostgreSQL for persistent storage.
"""
import uuid
import time
import copy
import json
import hashlib
import logging
import asyncio
from typing import Dict, Optional, List, Any, Any
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from core.config import settings
from core.redis_client import get_redis_client
from utils.system_design.models import Session as SessionModel, CanvasVersion, ChatMessage, Evaluation
from utils.system_design.question_service import QuestionService
from utils.system_design.evaluator import EvaluationEngine
from utils.system_design.orchestrator import ConversationOrchestrator
from utils.system_design.canvas_parser import CanvasParser
from utils.system_design.guardrails import guardrails
from models.interview_system_design import InterviewSystemDesign
from models.interview_analysis_table import InterviewAnalysisTable
from schemas.system_design import (
    SessionCreateRequest, SessionResponse, QuestionResponse, QuestionsResponse,
    ChatMessageRequest, ChatMessageResponse, CanvasUpdateRequest, CanvasUpdateResponse,
    ChatHistoryResponse, FinalReportResponse, ProactivePromptResponse
)


# In-memory session storage (for backward compatibility during migration)
# Key: (candidate_id, question_uuid) tuple
sessions: Dict[tuple, SessionModel] = {}

# Redis TTL for system design sessions (6 hours)
REDIS_SESSION_TTL = 6 * 3600

# Redis TTL for question metadata (1 hour - questions don't change often)
REDIS_QUESTION_METADATA_TTL = 3600

# Redis TTL for question metadata (1 hour - questions don't change often)
REDIS_QUESTION_METADATA_TTL = 3600


class SystemDesignService:
    """Service for managing system design interviews."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.question_service = QuestionService(db)
        self.evaluator = EvaluationEngine()
        self.orchestrator = ConversationOrchestrator()
        self.canvas_parser = CanvasParser()
        try:
            self.redis_client = get_redis_client()
        except Exception as e:
            logger.warning(f"Redis client initialization failed: {e}. Continuing without Redis.")
            self.redis_client = None
    
    # ==================== Redis Helper Methods ====================
    
    def _get_redis_session_key(self, candidate_id: str, question_uuid: str) -> str:
        """Get Redis key for session."""
        return f"candidate:{candidate_id}:system_design:{question_uuid}:session"
    
    def _get_redis_chat_key(self, candidate_id: str, question_uuid: str) -> str:
        """Get Redis key for chat messages."""
        return f"candidate:{candidate_id}:system_design:{question_uuid}:chat"
    
    def _get_redis_question_metadata_key(self, question_uuid: str) -> str:
        """Get Redis key for question metadata."""
        return f"system_design:question_metadata:{question_uuid}"
    
    def _get_question_metadata(self, question_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Get question metadata with Redis caching and DB fallback.
        
        Strategy:
        1. Try Redis cache (fast)
        2. Fallback to database (slower but reliable)
        3. Cache in Redis for future requests
        
        Args:
            question_uuid: UUID of the question
            
        Returns:
            Dictionary with question metadata, or None if question not found
        """
        if not question_uuid:
            return None
        
        redis_key = self._get_redis_question_metadata_key(question_uuid)
        
        # Step 1: Try Redis cache first (fast)
        if self.redis_client:
            try:
                cached_metadata = self.redis_client.get(redis_key)
                if cached_metadata:
                    try:
                        metadata = json.loads(cached_metadata)
                        logger.debug(f"[CACHE] ✅ Retrieved question metadata from Redis for {question_uuid}")
                        return metadata
                    except json.JSONDecodeError as e:
                        logger.warning(f"[CACHE] Failed to parse cached metadata for {question_uuid}: {e}")
                        # Continue to DB fallback
            except Exception as e:
                logger.warning(f"[CACHE] Redis read failed for question metadata {question_uuid}: {e}")
                # Continue to DB fallback - Redis failure is not critical
        
        # Step 2: Fallback to database (reliable)
        try:
            question = self.question_service.get_question_by_id(question_uuid)
            if not question:
                logger.warning(f"[CACHE] Question {question_uuid} not found in database")
                return None
            
            # Extract metadata safely with fallbacks
            metadata = {
                "uuid": question.uuid,
                "question": question.question,
                "evaluation_criteria": question.evaluation_criteria,
                "tags": question.tags if question.tags else [],
                "domain": getattr(question, 'domain', None),
                "complexity": getattr(question, 'complexity', None),
                "estimated_time_minutes": getattr(question, 'estimated_time_minutes', None),
                "guidance_prompts": getattr(question, 'guidance_prompts', {}) or {},
                "expected_components": getattr(question, 'expected_components', []) or [],
                "common_pitfalls": getattr(question, 'common_pitfalls', {}) or {},
                "hints": getattr(question, 'hints', {}) or {},
                "proactive_prompt_templates": getattr(question, 'proactive_prompt_templates', {}) or {},
                "functional_requirements_template": getattr(question, 'functional_requirements_template', None),
                "non_functional_requirements_template": getattr(question, 'non_functional_requirements_template', None),
                "evaluation_context": getattr(question, 'evaluation_context', {}) or {}
            }
            
            # Step 3: Cache in Redis for future requests (non-blocking)
            if self.redis_client:
                try:
                    metadata_json = json.dumps(metadata)
                    self.redis_client.setex(redis_key, REDIS_QUESTION_METADATA_TTL, metadata_json)
                    logger.debug(f"[CACHE] ✅ Cached question metadata in Redis for {question_uuid} (TTL: {REDIS_QUESTION_METADATA_TTL}s)")
                except Exception as e:
                    # Redis cache write failure is not critical - we still have the data from DB
                    logger.warning(f"[CACHE] Failed to cache question metadata in Redis for {question_uuid}: {e}")
            
            logger.debug(f"[CACHE] ✅ Retrieved question metadata from database for {question_uuid}")
            return metadata
            
        except Exception as e:
            logger.error(f"[CACHE] ❌ Failed to get question metadata from database for {question_uuid}: {e}")
            return None
    
    def _save_session_to_redis(self, candidate_id: str, question_uuid: str, session: SessionModel) -> bool:
        """Save session to Redis (soft save)."""
        if not self.redis_client:
            return False
        try:
            redis_key = self._get_redis_session_key(candidate_id, question_uuid)
            session_dict = session.model_dump()
            # Convert timestamps to ISO format for JSON serialization
            if session_dict.get('last_activity_time'):
                session_dict['last_activity_time'] = datetime.fromtimestamp(session_dict['last_activity_time']).isoformat()
            if session_dict.get('last_drawing_activity_time'):
                session_dict['last_drawing_activity_time'] = datetime.fromtimestamp(session_dict['last_drawing_activity_time']).isoformat()
            if session_dict.get('last_prompt_time'):
                session_dict['last_prompt_time'] = datetime.fromtimestamp(session_dict['last_prompt_time']).isoformat()
            if session_dict.get('last_poll_time'):
                session_dict['last_poll_time'] = datetime.fromtimestamp(session_dict['last_poll_time']).isoformat()
            
            self.redis_client.setex(
                redis_key,
                REDIS_SESSION_TTL,
                json.dumps(session_dict)
            )
            logger.debug(f"[REDIS] Saved session to Redis: {redis_key}")
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Failed to save session to Redis: {e}")
            return False
    
    def _load_session_from_redis(self, candidate_id: str, question_uuid: str) -> Optional[SessionModel]:
        """Load session from Redis."""
        if not self.redis_client:
            return None
        try:
            redis_key = self._get_redis_session_key(candidate_id, question_uuid)
            session_data = self.redis_client.get(redis_key)
            if session_data:
                session_dict = json.loads(session_data)
                # Convert ISO timestamps back to unix timestamps
                if session_dict.get('last_activity_time'):
                    session_dict['last_activity_time'] = datetime.fromisoformat(session_dict['last_activity_time']).timestamp()
                if session_dict.get('last_drawing_activity_time'):
                    session_dict['last_drawing_activity_time'] = datetime.fromisoformat(session_dict['last_drawing_activity_time']).timestamp()
                if session_dict.get('last_prompt_time'):
                    session_dict['last_prompt_time'] = datetime.fromisoformat(session_dict['last_prompt_time']).timestamp()
                if session_dict.get('last_poll_time'):
                    session_dict['last_poll_time'] = datetime.fromisoformat(session_dict['last_poll_time']).timestamp()
                
                return SessionModel(**session_dict)
        except Exception as e:
            logger.warning(f"[REDIS] Failed to load session from Redis: {e}")
        return None
    
    def _save_chat_to_redis(self, candidate_id: str, question_uuid: str, message: ChatMessage) -> bool:
        """Save chat message to Redis (soft save)."""
        if not self.redis_client:
            return False
        try:
            chat_key = self._get_redis_chat_key(candidate_id, question_uuid)
            message_dict = message.model_dump()
            if message_dict.get('timestamp'):
                message_dict['timestamp'] = datetime.fromisoformat(message_dict['timestamp']) if isinstance(message_dict['timestamp'], str) else message_dict['timestamp']
            message_dict['timestamp'] = datetime.utcnow().isoformat()
            
            self.redis_client.lpush(chat_key, json.dumps(message_dict))
            self.redis_client.expire(chat_key, REDIS_SESSION_TTL)
            logger.debug(f"[REDIS] Saved chat message to Redis")
            return True
        except Exception as e:
            logger.warning(f"[REDIS] Failed to save chat to Redis: {e}")
            return False
    
    def _load_chat_from_redis(self, candidate_id: str, question_uuid: str) -> List[ChatMessage]:
        """Load chat messages from Redis."""
        if not self.redis_client:
            return []
        try:
            chat_key = self._get_redis_chat_key(candidate_id, question_uuid)
            messages_data = self.redis_client.lrange(chat_key, 0, -1)
            messages = []
            for msg_data in reversed(messages_data):  # Reverse to get chronological order
                msg_dict = json.loads(msg_data)
                messages.append(ChatMessage(**msg_dict))
            return messages
        except Exception as e:
            logger.warning(f"[REDIS] Failed to load chat from Redis: {e}")
        return []
    
    # ==================== PostgreSQL Helper Methods ====================
    
    async def _save_session_to_postgresql(self, candidate_id: str, question_uuid: str, session: SessionModel, retry_count: int = 3) -> bool:
        """Save session to PostgreSQL with retry (hard save)."""
        for attempt in range(retry_count):
            try:
                # Convert chat history to JSONB array
                chat_messages_jsonb = [
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "timestamp": msg.timestamp or datetime.utcnow().isoformat()
                    }
                    for msg in session.chat_history
                ]
                
                db_record = self.db.query(InterviewSystemDesign).filter(
                    InterviewSystemDesign.candidate_id == candidate_id,
                    InterviewSystemDesign.question_uuid == question_uuid
                ).first()
                
                if not db_record:
                    # Create new record
                    db_record = InterviewSystemDesign(
                        candidate_id=candidate_id,
                        question_uuid=question_uuid,
                        score=None,
                        diagram=None,
                        current_canvas=session.current_canvas,
                        previous_canvas=session.previous_canvas,
                        chat_messages=chat_messages_jsonb,
                        last_activity_time=datetime.fromtimestamp(session.last_activity_time) if session.last_activity_time else None,
                        last_drawing_activity_time=datetime.fromtimestamp(session.last_drawing_activity_time) if session.last_drawing_activity_time else None,
                        last_prompt_time=datetime.fromtimestamp(session.last_prompt_time) if session.last_prompt_time else None,
                        last_poll_time=datetime.fromtimestamp(session.last_poll_time) if session.last_poll_time else None,
                        prompt_history=session.prompt_history or [],
                        milestones=session.milestones or {},
                        last_canvas_hash=session.last_canvas_hash,
                        status='in_progress' if session.current_canvas else 'assigned',
                        created_at=datetime.utcnow()
                    )
                    self.db.add(db_record)
                else:
                    # Update existing record (preserve score and diagram if they exist)
                    db_record.current_canvas = session.current_canvas
                    db_record.previous_canvas = session.previous_canvas
                    db_record.chat_messages = chat_messages_jsonb
                    if session.last_activity_time:
                        db_record.last_activity_time = datetime.fromtimestamp(session.last_activity_time)
                    if session.last_drawing_activity_time:
                        db_record.last_drawing_activity_time = datetime.fromtimestamp(session.last_drawing_activity_time)
                    if session.last_prompt_time:
                        db_record.last_prompt_time = datetime.fromtimestamp(session.last_prompt_time)
                    if session.last_poll_time:
                        db_record.last_poll_time = datetime.fromtimestamp(session.last_poll_time)
                    db_record.prompt_history = session.prompt_history or []
                    db_record.milestones = session.milestones or {}
                    db_record.last_canvas_hash = session.last_canvas_hash
                    # Update status if not already evaluated/submitted
                    if db_record.status not in ['submitted', 'evaluated']:
                        db_record.status = 'in_progress' if session.current_canvas else 'assigned'
                
                self.db.commit()
                logger.debug(f"[POSTGRES] Saved session to PostgreSQL (attempt {attempt+1})")
                return True
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 1 * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(f"[POSTGRES] Session save failed (attempt {attempt+1}/{retry_count}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self.db.rollback()
                else:
                    logger.error(f"[POSTGRES] Session save failed after {retry_count} attempts: {e}")
                    self.db.rollback()
        return False
    
    async def _save_chat_message_to_postgresql(self, candidate_id: str, question_uuid: str, message: ChatMessage, retry_count: int = 3) -> bool:
        """Save chat message to PostgreSQL by appending to JSONB array (hard save)."""
        for attempt in range(retry_count):
            try:
                db_record = self.db.query(InterviewSystemDesign).filter(
                    InterviewSystemDesign.candidate_id == candidate_id,
                    InterviewSystemDesign.question_uuid == question_uuid
                ).first()
                
                if not db_record:
                    # Create new record if it doesn't exist
                    db_record = InterviewSystemDesign(
                        candidate_id=candidate_id,
                        question_uuid=question_uuid,
                        chat_messages=[],
                        status='in_progress'
                    )
                    self.db.add(db_record)
                
                # Get current chat messages
                chat_messages = db_record.chat_messages or []
                
                # Check if message already exists (avoid duplicates)
                message_exists = any(
                    msg.get('content') == message.content and msg.get('role') == message.role
                    for msg in chat_messages
                )
                
                if message_exists:
                    logger.debug(f"[POSTGRES] Chat message already exists, skipping")
                    return True
                
                # Append new message
                new_message = {
                    "role": message.role,
                    "content": message.content,
                    "timestamp": message.timestamp or datetime.utcnow().isoformat()
                }
                chat_messages.append(new_message)
                db_record.chat_messages = chat_messages
                
                self.db.commit()
                logger.debug(f"[POSTGRES] Saved chat message to PostgreSQL (attempt {attempt+1})")
                return True
            except Exception as e:
                if attempt < retry_count - 1:
                    wait_time = 1 * (2 ** attempt)
                    logger.warning(f"[POSTGRES] Chat message save failed (attempt {attempt+1}/{retry_count}): {e}. Retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    self.db.rollback()
                else:
                    logger.error(f"[POSTGRES] Chat message save failed after {retry_count} attempts: {e}")
                    self.db.rollback()
        return False
    
    async def _save_canvas_version_to_postgresql(self, candidate_id: str, question_uuid: str, canvas_json: dict, 
                                                  version: int, components: int, edges: int, action: str, retry_count: int = 3) -> bool:
        """Save canvas version - no-op since we're not storing versions anymore."""
        # Canvas versions are no longer stored separately
        # The current_canvas in interview_system_design is the latest state
        logger.debug(f"[POSTGRES] Canvas version save skipped (versions not stored)")
        return True
    
    def _load_session_from_postgresql(self, candidate_id: str, question_uuid: str) -> Optional[SessionModel]:
        """Load session from PostgreSQL."""
        try:
            db_record = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id,
                InterviewSystemDesign.question_uuid == question_uuid
            ).first()
            
            if not db_record:
                return None
            
            # Get question text using cached method (Redis -> DB fallback)
            question_metadata = self._get_question_metadata(question_uuid)
            question_text = question_metadata.get("question", "") if question_metadata else ""
            
            # Parse chat messages from JSONB array
            chat_messages_jsonb = db_record.chat_messages or []
            chat_history = [
                ChatMessage(
                    role=msg.get('role', 'user'),
                    content=msg.get('content', ''),
                    timestamp=msg.get('timestamp')
                )
                for msg in chat_messages_jsonb
            ]
            
            # Canvas versions and evaluations are no longer stored separately
            # They're part of the session model but not persisted
            canvas_versions = []
            evaluations = []
            
            session = SessionModel(
                candidate_id=candidate_id,
                question_id=question_uuid,
                question_text=question_text,
                canvas_versions=canvas_versions,
                chat_history=chat_history,
                evaluations=evaluations,
                current_canvas=db_record.current_canvas,
                previous_canvas=db_record.previous_canvas,
                last_activity_time=db_record.last_activity_time.timestamp() if db_record.last_activity_time else None,
                last_drawing_activity_time=db_record.last_drawing_activity_time.timestamp() if db_record.last_drawing_activity_time else None,
                last_prompt_time=db_record.last_prompt_time.timestamp() if db_record.last_prompt_time else None,
                last_poll_time=db_record.last_poll_time.timestamp() if db_record.last_poll_time else None,
                prompt_history=db_record.prompt_history or [],
                milestones=db_record.milestones or {},
                last_canvas_hash=db_record.last_canvas_hash,
                created_at=db_record.created_at.isoformat() if db_record.created_at else None,
                ended_at=db_record.submitted_at.isoformat() if db_record.submitted_at else None
            )
            
            return session
        except Exception as e:
            logger.error(f"[POSTGRES] Failed to load session from PostgreSQL: {e}")
            return None
    
    def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        """Create a new interview session."""
        # Get candidate_id from request (should be set by route from auth)
        candidate_id = request.candidate_id
        if not candidate_id:
            raise ValueError("candidate_id is required for session creation")
        
        # Determine which question to use
        question_uuid = None
        question_text = request.question_text
        
        # PRIORITY 1: Check for pre-assigned question in interview_system_design table
        from services.question_assignment_service import QuestionAssignmentService
        assignment_service = QuestionAssignmentService(self.db)
        assigned_question_uuid = assignment_service.get_assigned_question(candidate_id)
        
        if assigned_question_uuid:
            # Use pre-assigned question
            question_uuid = assigned_question_uuid
            logger.info(f"[SESSION CREATION] ✅ Using pre-assigned question for candidate {candidate_id}")
            logger.info(f"[SESSION CREATION]    Question UUID: {question_uuid}")
        else:
            # PRIORITY 2: Use explicit question_uuid from request (if no pre-assigned question)
            if request.question_uuid:
                # Use explicit question UUID
                logger.info(f"[SESSION CREATION] Using explicit question_uuid from request: {request.question_uuid} for candidate {candidate_id}")
                question_uuid = request.question_uuid
                logger.info(f"[SESSION CREATION] ✅ Using question UUID: {question_uuid}")
            elif request.tag:
                # Get random question by tag
                logger.info(f"[SESSION CREATION] Selecting random question by tag '{request.tag}' for candidate {candidate_id}")
                question = self.question_service.get_random_question_by_tag(request.tag)
                if question:
                    question_uuid = question.uuid
                    logger.info(f"[SESSION CREATION] ✅ Selected question UUID: {question_uuid} (tag: {request.tag})")
                else:
                    logger.error(f"[SESSION CREATION] No questions found with tag '{request.tag}' for candidate {candidate_id}")
                    raise ValueError(f"No questions found with tag: {request.tag}")
            elif not question_text:
                # Default: use URL shortener question
                logger.info(f"[SESSION CREATION] Using default question for candidate {candidate_id}")
                question_uuid = "q1-normal-hld-url-shortener"
                logger.info(f"[SESSION CREATION] ✅ Using default question UUID: {question_uuid}")
            else:
                # If question_text provided but no UUID, we can't create a proper session
                raise ValueError("question_uuid is required when question_text is provided")
        
        # Ensure we have a question_uuid (required for composite key)
        if not question_uuid:
            # If no question_uuid, we can't create a proper session
            raise ValueError("question_uuid is required for session creation")
        
        # Fetch question metadata ONCE using cached method (Redis -> DB fallback)
        question_metadata = self._get_question_metadata(question_uuid)
        if not question_metadata:
            logger.error(f"[SESSION CREATION] Question {question_uuid} not found in database for candidate {candidate_id}")
            raise ValueError(f"Question with UUID {question_uuid} not found")
        
        # Extract question text from metadata
        question_text = question_metadata.get("question") or question_text
        if not question_text:
            raise ValueError(f"Question text not available for UUID {question_uuid}")
        
        # Use composite key: (candidate_id, question_uuid)
        session_key = (candidate_id, question_uuid)
        
        # Check if session already exists (load existing session if available)
        existing_session = self.get_session(candidate_id, question_uuid)
        
        if existing_session and existing_session.current_canvas:
            # Session exists with canvas data - return it
            logger.info(f"[SESSION CREATION] ✅ Loaded existing session with canvas for candidate {candidate_id}")
            return SessionResponse(
                question_text=existing_session.question_text or question_text,
                question_uuid=question_uuid,
                current_canvas=existing_session.current_canvas
            )
        
        # Create new session (or use existing empty session)
        if not existing_session:
            session = SessionModel(
                candidate_id=candidate_id,
                question_id=question_uuid,
                question_text=question_text,
                canvas_versions=[],
                chat_history=[],
                evaluations=[],
                current_canvas=None,
                previous_canvas=None,
                last_activity_time=time.time(),
                last_drawing_activity_time=None,
                last_prompt_time=None,
                last_poll_time=None,
                prompt_history=[],
                milestones={},
                last_canvas_hash=None
            )
            
            # 1. SOFT SAVE: Save to Redis (immediate)
            self._save_session_to_redis(candidate_id, question_uuid, session)
            
            # 2. HARD SAVE: Save to PostgreSQL (async, non-blocking)
            asyncio.create_task(self._save_session_to_postgresql(candidate_id, question_uuid, session))
            
            # 3. Store in-memory (for backward compatibility)
            sessions[session_key] = session
        else:
            # Use existing session (update question_text if needed)
            session = existing_session
            if not session.question_text:
                session.question_text = question_text
        
        # No need to verify again - we already fetched and validated question_metadata above
        return SessionResponse(
            question_text=session.question_text or question_text,
            question_uuid=question_uuid,
            current_canvas=session.current_canvas
        )
    
    def get_session(self, candidate_id: str, question_uuid: str) -> SessionModel:
        """Get session by composite key (candidate_id, question_uuid), creating if it doesn't exist."""
        session_key = (candidate_id, question_uuid)
        
        # 1. Try in-memory cache first (fastest)
        if session_key in sessions:
            return sessions[session_key]
        
        # 2. Try Redis (fast)
        session = self._load_session_from_redis(candidate_id, question_uuid)
        if session:
            # Warm in-memory cache
            sessions[session_key] = session
            logger.info(f"[SESSION] Loaded from Redis cache")
            return session
        
        # 3. Try PostgreSQL (slower, but complete)
        session = self._load_session_from_postgresql(candidate_id, question_uuid)
        if session:
            # Warm Redis cache
            self._save_session_to_redis(candidate_id, question_uuid, session)
            # Warm in-memory cache
            sessions[session_key] = session
            logger.info(f"[SESSION] Loaded from PostgreSQL")
            return session
        
        # 4. Create new session if not found
        question = self.question_service.get_question_by_id(question_uuid)
        if not question:
            raise ValueError(f"Question with UUID {question_uuid} not found")
        
        question_text = question.question
        
        session = SessionModel(
            candidate_id=candidate_id,
            question_id=question_uuid,
            question_text=question_text,
            canvas_versions=[],
            chat_history=[],
            evaluations=[],
            current_canvas=None,
            previous_canvas=None,
            last_activity_time=time.time(),
            last_drawing_activity_time=None,
            last_prompt_time=None,
            last_poll_time=None,
            prompt_history=[],
            milestones={},
            last_canvas_hash=None
        )
        
        # Save to Redis and PostgreSQL
        self._save_session_to_redis(candidate_id, question_uuid, session)
        asyncio.create_task(self._save_session_to_postgresql(candidate_id, question_uuid, session))
        
        sessions[session_key] = session
        logger.info(f"[SESSION RECREATE] Created new session for candidate {candidate_id}, question {question_uuid}: {question_text[:100]}...")
        
        return session
    
    def get_questions(self, tag: Optional[str] = None) -> QuestionsResponse:
        """Get all questions, optionally filtered by tag."""
        import json
        if tag:
            questions = self.question_service.get_questions_by_tag(tag)
        else:
            questions = self.question_service.get_all_questions()
        
        question_responses = []
        for q in questions:
            tags_data = json.loads(q.tags) if isinstance(q.tags, str) else q.tags
            # Convert list to dictionary format if needed
            if isinstance(tags_data, list):
                tags_data = {tag: True for tag in tags_data}
            elif not isinstance(tags_data, dict):
                tags_data = None
            question_responses.append(QuestionResponse(
                uuid=q.uuid,
                question_id=q.uuid,
                question=q.question,
                evaluation_criteria=q.evaluation_criteria[:200] + "..." if len(q.evaluation_criteria) > 200 else q.evaluation_criteria,
                tags=tags_data
            ))
        
        return QuestionsResponse(questions=question_responses)
    
    def get_question(self, uuid: str) -> QuestionResponse:
        """Get a specific question by UUID."""
        import json
        question = self.question_service.get_question_by_id(uuid)
        if not question:
            raise ValueError(f"Question with UUID {uuid} not found")
        
        tags_data = json.loads(question.tags) if isinstance(question.tags, str) else question.tags
        # Convert list to dictionary format if needed
        if isinstance(tags_data, list):
            tags_data = {tag: True for tag in tags_data}
        elif not isinstance(tags_data, dict):
            tags_data = None
        return QuestionResponse(
            uuid=question.uuid,
            question_id=question.uuid,
            question=question.question,
            evaluation_criteria=question.evaluation_criteria,
            tags=tags_data
        )
    
    def get_random_question(self, tag: Optional[str] = None) -> QuestionResponse:
        """Get a random question, optionally filtered by tag."""
        import json
        if tag:
            question = self.question_service.get_random_question_by_tag(tag)
        else:
            question = self.question_service.get_random_question()
        
        if not question:
            raise ValueError("No questions found")
        
        tags_data = json.loads(question.tags) if isinstance(question.tags, str) else question.tags
        # Convert list to dictionary format if needed
        if isinstance(tags_data, list):
            tags_data = {tag: True for tag in tags_data}
        elif not isinstance(tags_data, dict):
            tags_data = None
        return QuestionResponse(
            uuid=question.uuid,
            question_id=question.uuid,
            question=question.question,
            evaluation_criteria=question.evaluation_criteria,
            tags=tags_data
        )
    
    async def update_canvas(self, request: CanvasUpdateRequest, candidate_id: str, question_uuid: str) -> CanvasUpdateResponse:
        """Handle canvas updates (save, submit, or update)."""
        if not question_uuid:
            raise ValueError("question_uuid is required")
        session = self.get_session(candidate_id, question_uuid)
        
        # For "update" action, optimize by checking hash first
        if request.action == "update":
            canvas_json = request.canvas_data.model_dump()
            
            # Quick hash calculation for change detection (component count + edge count)
            elements = canvas_json.get("elements", [])
            component_count = len([e for e in elements if e.get("type") not in ["arrow", "line"]])
            edge_count = len([e for e in elements if e.get("type") in ["arrow", "line"]])
            
            canvas_hash = hashlib.md5(
                json.dumps({
                    "components": component_count,
                    "edges": edge_count
                }).encode()
            ).hexdigest()
            
            # Skip processing if no meaningful change
            if session.last_canvas_hash and session.last_canvas_hash == canvas_hash:
                return CanvasUpdateResponse(status="no_change")
            
            # Update hash and canvas
            session.last_canvas_hash = canvas_hash
            session.current_canvas = canvas_json
            session.last_activity_time = time.time()
            
            # SOFT SAVE: Update Redis (immediate)
            self._save_session_to_redis(candidate_id, question_uuid, session)
            
            # Don't do expensive parsing for "update" action
            return CanvasUpdateResponse(status="updated")
        
        # For "save" and "submit", do full processing
        # Parse canvas data
        canvas_json = request.canvas_data.model_dump()
        parsed_data = self.canvas_parser.parse(canvas_json)
        
        # Store previous canvas BEFORE checking for changes
        old_current_canvas = copy.deepcopy(session.current_canvas) if session.current_canvas else None
        
        # Check for significant changes
        significant_change_detected = False
        canvas_to_compare = session.previous_canvas if session.previous_canvas else session.current_canvas
        
        if canvas_to_compare:
            old_component_count = self.canvas_parser.parse(canvas_to_compare)["component_count"]
            new_component_count = parsed_data["component_count"]
            
            if self.orchestrator.detect_significant_change(canvas_to_compare, canvas_json):
                current_time = time.time()
                significant_change_detected = True
                
                session.previous_canvas = copy.deepcopy(old_current_canvas) if old_current_canvas else (copy.deepcopy(canvas_to_compare) if canvas_to_compare else None)
                session.last_drawing_activity_time = current_time
                session.last_activity_time = current_time
        
        # Always update current_canvas
        session.current_canvas = canvas_json
        
        # Update hash for future comparisons
        elements = canvas_json.get("elements", [])
        component_count = len([e for e in elements if e.get("type") not in ["arrow", "line"]])
        edge_count = len([e for e in elements if e.get("type") in ["arrow", "line"]])
        session.last_canvas_hash = hashlib.md5(
            json.dumps({
                "components": component_count,
                "edges": edge_count
            }).encode()
        ).hexdigest()
        
        if request.action == "save":
            # Save draft without evaluation
            session.last_activity_time = time.time()
            version = CanvasVersion(
                version=len(session.canvas_versions) + 1,
                data=canvas_json,
                components=parsed_data["component_count"],
                edges=parsed_data["edge_count"],
                timestamp=parsed_data.get("timestamp")
            )
            session.canvas_versions.append(version)
            
            # 1. SOFT SAVE: Save to Redis (immediate)
            self._save_session_to_redis(candidate_id, question_uuid, session)
            
            # 2. HARD SAVE: Save canvas version to PostgreSQL (async)
            asyncio.create_task(self._save_canvas_version_to_postgresql(
                candidate_id, question_uuid, canvas_json, version.version,
                parsed_data["component_count"], parsed_data["edge_count"], "save"
            ))
            
            return CanvasUpdateResponse(status="saved", version=version.version)
        
        elif request.action == "submit":
            # Evaluate figure + chat
            session.last_activity_time = time.time()
            
            # Use more chat context - last 30 messages or all if less than 30
            if session.chat_history:
                if len(session.chat_history) <= 30:
                    latest_chat = session.chat_history
                else:
                    latest_chat = session.chat_history[-30:]
                chat_text = "\n".join([msg.content for msg in latest_chat])
            else:
                chat_text = ""
            
            # Fetch evaluation criteria using cached method (Redis -> DB fallback)
            evaluation_criteria = None
            evaluation_context = None
            if session.question_id:
                question_metadata = self._get_question_metadata(session.question_id)
                if question_metadata:
                    evaluation_criteria = question_metadata.get("evaluation_criteria")
                    evaluation_context = question_metadata.get("evaluation_context")
                    logger.info(f"[CANVAS SUBMIT] Using evaluation_criteria from cached metadata for question {session.question_id}")
                else:
                    logger.warning(f"[CANVAS SUBMIT] Question {session.question_id} not found in database")
            
            evaluation = await self.evaluator.evaluate(
                canvas_json=canvas_json,
                chat_text=chat_text,
                question_text=session.question_text,
                evaluation_criteria=evaluation_criteria,
                evaluation_context=evaluation_context
            )
            
            # Save canvas version
            version = CanvasVersion(
                version=len(session.canvas_versions) + 1,
                data=canvas_json,
                components=parsed_data["component_count"],
                edges=parsed_data["edge_count"],
                timestamp=parsed_data.get("timestamp")
            )
            session.canvas_versions.append(version)
            
            # Save evaluation
            eval_obj = Evaluation(
                version=version.version,
                scores=evaluation["scores"],
                feedback=evaluation["feedback"],
                follow_up=evaluation.get("follow_up")
            )
            session.evaluations.append(eval_obj)
            
            # Format evaluation response and add to chat history (natural, conversational format)
            scores_str = ", ".join([f"{k}: {v:.1f}" for k, v in evaluation.get("scores", {}).items()])
            feedback_text = evaluation.get('feedback', 'No feedback available')
            follow_up_text = evaluation.get('follow_up', 'Continue refining your design.')
            evaluation_message = f"""{feedback_text}

**Scores:** {scores_str}

**Follow-up:** {follow_up_text}"""
            
            # Add evaluation to chat history
            eval_chat_msg = ChatMessage(
                role="assistant",
                content=evaluation_message,
                timestamp=None
            )
            session.chat_history.append(eval_chat_msg)
            
            # 1. SOFT SAVE: Save to Redis (immediate)
            self._save_session_to_redis(candidate_id, question_uuid, session)
            self._save_chat_to_redis(candidate_id, question_uuid, eval_chat_msg)
            
            # 2. HARD SAVE: Save to PostgreSQL (immediate - critical data)
            try:
                # Save chat message (evaluation message)
                await self._save_chat_message_to_postgresql(candidate_id, question_uuid, eval_chat_msg)
                
                # Save final diagram and score to interview_system_design
                interview_record = self.db.query(InterviewSystemDesign).filter(
                    InterviewSystemDesign.candidate_id == candidate_id,
                    InterviewSystemDesign.question_uuid == question_uuid
                ).first()
                
                avg_score = sum(evaluation["scores"].values()) / len(evaluation["scores"]) if evaluation["scores"] else 0
                final_score = int(round(avg_score * 20))  # Convert 1-5 to 0-100
                
                if interview_record:
                    # Update existing record
                    interview_record.diagram = json.dumps(canvas_json)
                    interview_record.score = final_score
                    interview_record.current_canvas = canvas_json  # Update current canvas
                    interview_record.submitted_at = datetime.utcnow()
                    interview_record.status = 'evaluated'
                    # Update chat messages (include evaluation message)
                    chat_messages = interview_record.chat_messages or []
                    eval_msg_dict = {
                        "role": eval_chat_msg.role,
                        "content": eval_chat_msg.content,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    chat_messages.append(eval_msg_dict)
                    interview_record.chat_messages = chat_messages
                else:
                    # Create new record
                    chat_messages = [{
                        "role": eval_chat_msg.role,
                        "content": eval_chat_msg.content,
                        "timestamp": datetime.utcnow().isoformat()
                    }]
                    interview_record = InterviewSystemDesign(
                        candidate_id=candidate_id,
                        question_uuid=question_uuid,
                        diagram=json.dumps(canvas_json),
                        score=final_score,
                        current_canvas=canvas_json,
                        chat_messages=chat_messages,
                        submitted_at=datetime.utcnow(),
                        status='evaluated'
                    )
                    self.db.add(interview_record)
                
                self.db.commit()
                logger.info(f"[CANVAS SUBMIT] ✅ Saved final diagram and score to PostgreSQL")
                
            except Exception as e:
                self.db.rollback()
                logger.error(f"[CANVAS SUBMIT] ❌ PostgreSQL save failed: {e}")
                # Don't fail - Redis has the data, background sync will handle it
            
            return CanvasUpdateResponse(
                status="evaluated",
                evaluation=evaluation,
                version=version.version,
                evaluation_message=evaluation_message
            )
        
        raise ValueError("Invalid action")
    
    async def send_message(self, request: ChatMessageRequest, candidate_id: str, question_uuid: str) -> ChatMessageResponse:
        """Send a chat message."""
        if not question_uuid:
            raise ValueError("question_uuid is required")
        session = self.get_session(candidate_id, question_uuid)
        
        # Sanitize user message
        sanitized_message, is_safe, warning = guardrails.sanitize_input(request.message)
        if not is_safe:
            print(f"[GUARDRAIL] User message sanitized at entry point: {warning}")
        
        # Update activity tracking
        session.last_activity_time = time.time()
        
        # Update canvas if provided in request (use latest canvas state from frontend)
        if request.canvas_data:
            canvas_json = request.canvas_data.model_dump()
            session.current_canvas = canvas_json
            session.last_activity_time = time.time()
        
        # Add sanitized user message to chat history
        user_msg = ChatMessage(
            role="user",
            content=sanitized_message,
            timestamp=None
        )
        session.chat_history.append(user_msg)
        
        # 1. SOFT SAVE: Save to Redis (immediate)
        self._save_chat_to_redis(candidate_id, question_uuid, user_msg)
        self._save_session_to_redis(candidate_id, question_uuid, session)
        
        # 2. HARD SAVE: Save to PostgreSQL (immediate - chat is important)
        await self._save_chat_message_to_postgresql(candidate_id, question_uuid, user_msg)
        
        # Check if message triggers AI response
        should_respond = self.orchestrator.should_respond(
            message=sanitized_message,
            session=session
        )
        
        if should_respond:
            # Get latest canvas - prefer canvas from request, then session, then last version
            if request.canvas_data:
                latest_canvas = request.canvas_data.model_dump()
            else:
                latest_canvas = session.current_canvas
                if not latest_canvas and session.canvas_versions:
                    latest_canvas = session.canvas_versions[-1].data
            
            # Get question metadata for orchestrator (cached - Redis -> DB fallback)
            question_metadata = self._get_question_metadata(question_uuid) if question_uuid else None
            
            # Generate regular AI response (evaluation is only triggered via explicit actions like canvas submission)
            try:
                ai_response = await self.orchestrator.generate_response(
                    message=sanitized_message,
                    canvas_data=latest_canvas,
                    chat_history=session.chat_history[-5:],
                    question_text=session.question_text,
                    question_metadata=question_metadata  # Pass cached metadata for future adaptive responses
                )
                
                if ai_response and "API Error" in ai_response:
                    ai_response = f"I'm here to help with your system design. However, there was an issue with the API. Please check your {settings.LLM_PROVIDER.upper()}_API_KEY configuration."
                
                ai_msg = ChatMessage(
                    role="assistant",
                    content=ai_response,
                    timestamp=None
                )
                session.chat_history.append(ai_msg)
                
                # 1. SOFT SAVE: Save to Redis (immediate)
                self._save_chat_to_redis(candidate_id, question_uuid, ai_msg)
                self._save_session_to_redis(candidate_id, question_uuid, session)
                
                # 2. HARD SAVE: Save to PostgreSQL (immediate - chat is important)
                await self._save_chat_message_to_postgresql(candidate_id, question_uuid, ai_msg)
                
                return ChatMessageResponse(
                    user_message=user_msg.model_dump(),
                    ai_response=ai_response
                )
            except Exception as e:
                print(f"Error generating AI response: {str(e)}")
                error_response = f"I encountered an issue generating a response. Please check your {settings.LLM_PROVIDER.upper()}_API_KEY configuration or try again later."
                ai_msg = ChatMessage(
                    role="assistant",
                    content=error_response,
                    timestamp=None
                )
                session.chat_history.append(ai_msg)
                
                # 1. SOFT SAVE: Save to Redis (immediate)
                self._save_chat_to_redis(candidate_id, question_uuid, ai_msg)
                self._save_session_to_redis(candidate_id, question_uuid, session)
                
                # 2. HARD SAVE: Save to PostgreSQL (immediate - chat is important)
                await self._save_chat_message_to_postgresql(candidate_id, question_uuid, ai_msg)
                
                return ChatMessageResponse(
                    user_message=user_msg.model_dump(),
                    ai_response=error_response
                )
        
        return ChatMessageResponse(user_message=user_msg.model_dump(), ai_response=None)
    
    def get_chat_history(self, candidate_id: str, question_uuid: str) -> ChatHistoryResponse:
        """Get full chat history for a session - Redis first, PostgreSQL fallback."""
        # 1. Try Redis first (fast - for active sessions)
        try:
            cached_messages = self._load_chat_from_redis(candidate_id, question_uuid)
            if cached_messages:
                logger.debug(f"[CHAT] Retrieved {len(cached_messages)} messages from Redis")
                return ChatHistoryResponse(messages=[msg.model_dump() for msg in cached_messages])
        except Exception as e:
            logger.warning(f"[CHAT] Redis read failed: {e}")
        
        # 2. Fallback to PostgreSQL (complete history)
        session = self.get_session(candidate_id, question_uuid)
        messages = [msg.model_dump() for msg in session.chat_history]
        
        # 3. Warm Redis cache (if we got messages from PostgreSQL)
        if messages and self.redis_client:
            try:
                chat_key = self._get_redis_chat_key(candidate_id, question_uuid)
                # Store all messages in Redis
                for msg in reversed(session.chat_history):  # Push in reverse order
                    self._save_chat_to_redis(candidate_id, question_uuid, msg)
                logger.debug(f"[CHAT] Warmed Redis cache with {len(messages)} messages")
            except Exception as e:
                logger.warning(f"[CHAT] Redis cache warm failed: {e}")
        
        return ChatHistoryResponse(messages=messages)
    
    async def check_proactive_prompts(self, candidate_id: str, question_uuid: str) -> ProactivePromptResponse:
        """Check if any proactive prompts should be triggered for the session."""
        session = self.get_session(candidate_id, question_uuid)
        prompt = await self.orchestrator.check_proactive_prompts(session)
        
        if prompt:
            # Update last prompt time to prevent duplicate prompts
            session.last_prompt_time = time.time()
            # Add to prompt history
            session.prompt_history.append(prompt)
            return ProactivePromptResponse(has_prompt=True, prompt=prompt)
        else:
            return ProactivePromptResponse(has_prompt=False, prompt=None)
    
    def _extract_strengths_and_improvements_simple(
        self,
        feedback: str,
        scores: Dict[str, float]
    ) -> Dict[str, List[str]]:
        """Extract key strengths and improvements using simple text parsing."""
        key_strengths = []
        things_to_improve = []
        
        if not feedback:
            return {"key_strengths": [], "things_to_improve": []}
        
        # Split feedback into sentences
        sentences = [s.strip() for s in feedback.split('.') if s.strip()]
        
        # Positive indicators
        positive_keywords = ["great", "excellent", "good", "well", "strong", "solid", "impressive", "correctly", "nice", "effective"]
        # Improvement indicators
        improvement_keywords = ["missing", "consider", "improve", "add", "should", "need", "lacks", "could", "better", "however", "but", "although"]
        
        for sentence in sentences:
            sentence_lower = sentence.lower()
            
            # Check for strengths
            if any(keyword in sentence_lower for keyword in positive_keywords):
                if len(sentence) < 200:  # Avoid very long sentences
                    key_strengths.append(sentence)
            
            # Check for improvements
            if any(keyword in sentence_lower for keyword in improvement_keywords):
                if len(sentence) < 200:
                    things_to_improve.append(sentence)
        
        # Also add strengths from high scores
        for category, score in scores.items():
            if score >= 4.0:
                category_name = category.replace('_', ' ').title()
                key_strengths.append(f"Strong performance in {category_name}")
            elif score <= 2.5:
                category_name = category.replace('_', ' ').title()
                things_to_improve.append(f"Needs improvement in {category_name}")
        
        # Deduplicate and limit
        return {
            "key_strengths": list(set(key_strengths))[:5],  # Top 5 strengths
            "things_to_improve": list(set(things_to_improve))[:5]  # Top 5 improvements
        }
    
    def _save_to_interview_analysis_table(
        self,
        candidate_id: str,
        final_report: Dict[str, Any],
        evaluation: Optional[Dict[str, Any]] = None
    ) -> None:
        """Save system design evaluation results to interview_analysis_table."""
        try:
            # Extract data from final_report
            avg_scores = final_report.get("average_scores", {})
            
            # Calculate overall score (0-100) from average scores
            if avg_scores:
                avg_score = sum(avg_scores.values()) / len(avg_scores)
                overall_score = int(round(avg_score * 20))  # Convert 1-5 to 0-100
            else:
                overall_score = None
            
            # Extract strengths and improvements
            feedback = evaluation.get("feedback", "") if evaluation else final_report.get("final_feedback", "")
            extraction = self._extract_strengths_and_improvements_simple(feedback, avg_scores)
            
            # Build system_design_analysis JSONB object
            system_design_analysis = {
                "score": overall_score,
                "key_strengths": extraction["key_strengths"],
                "things_to_improve": extraction["things_to_improve"],
                "summary": final_report.get("final_feedback", ""),
                "average_scores": avg_scores,  # Store detailed scores too
                "lowest_area": final_report.get("lowest_area"),
                "suggested_learning": final_report.get("suggested_learning", [])
            }
            
            # Get or create interview_analysis record
            interview_analysis = self.db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if interview_analysis:
                # Update existing record
                interview_analysis.system_design_analysis = system_design_analysis
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Updated system_design_analysis for candidate {candidate_id}")
            else:
                # Create new record
                interview_analysis = InterviewAnalysisTable(
                    candidate_id=candidate_id,
                    system_design_analysis=system_design_analysis
                )
                self.db.add(interview_analysis)
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Created new interview_analysis record for candidate {candidate_id}")
            
            self.db.commit()
            
        except Exception as e:
            logger.error(f"[INTERVIEW_ANALYSIS] ❌ Failed to save to interview_analysis_table: {e}")
            self.db.rollback()
            # Don't raise - this is non-critical, don't break the report generation
    
    async def generate_final_report(self, candidate_id: str, question_uuid: str) -> FinalReportResponse:
        """Generate final evaluation report for the session."""
        session = self.get_session(candidate_id, question_uuid)
        
        # Fetch evaluation_criteria using cached method (Redis -> DB fallback)
        evaluation_criteria = None
        evaluation_context = None
        if session.question_id:
            question_metadata = self._get_question_metadata(session.question_id)
            if question_metadata:
                evaluation_criteria = question_metadata.get("evaluation_criteria")
                evaluation_context = question_metadata.get("evaluation_context")
                logger.info(f"[FINAL REPORT] ✅ Using evaluation_criteria from cached metadata for question {session.question_id}")
            else:
                logger.warning(f"[FINAL REPORT] ⚠️  Question {session.question_id} not found in database, will use default evaluation criteria")
        
        # Generate final report
        report = await self.evaluator.generate_final_report(session, evaluation_criteria, evaluation_context)
        
        # Get the latest evaluation for extracting strengths/improvements
        latest_evaluation = None
        if session.evaluations:
            latest_evaluation = {
                "scores": session.evaluations[-1].scores,
                "feedback": session.evaluations[-1].feedback,
                "follow_up": session.evaluations[-1].follow_up
            }
        elif report.get("timeline"):
            # Extract from timeline if available
            latest_timeline_item = report.get("timeline", [])[-1] if report.get("timeline") else None
            if latest_timeline_item:
                latest_evaluation = {
                    "scores": latest_timeline_item.get("scores", {}),
                    "feedback": latest_timeline_item.get("feedback", ""),
                    "follow_up": latest_timeline_item.get("follow_up", "")
                }
        
        # Save to interview_analysis_table
        self._save_to_interview_analysis_table(candidate_id, report, latest_evaluation)
        
        return FinalReportResponse(**report)

