"""
System Design service for managing interview sessions, evaluations, and chat.
"""
import uuid
import time
import copy
import json
import hashlib
import logging
from typing import Dict, Optional, List
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)
from core.config import settings
from utils.system_design.models import Session as SessionModel, CanvasVersion, ChatMessage, Evaluation
from utils.system_design.question_service import QuestionService
from utils.system_design.evaluator import EvaluationEngine
from utils.system_design.orchestrator import ConversationOrchestrator
from utils.system_design.canvas_parser import CanvasParser
from utils.system_design.guardrails import guardrails
from schemas.system_design import (
    SessionCreateRequest, SessionResponse, QuestionResponse, QuestionsResponse,
    ChatMessageRequest, ChatMessageResponse, CanvasUpdateRequest, CanvasUpdateResponse,
    ProactivePromptResponse, ChatHistoryResponse, FinalReportResponse
)


# In-memory session storage (replace with database in production)
sessions: Dict[str, SessionModel] = {}


class SystemDesignService:
    """Service for managing system design interviews."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.question_service = QuestionService(db)
        self.evaluator = EvaluationEngine()
        self.orchestrator = ConversationOrchestrator()
        self.canvas_parser = CanvasParser()
    
    def create_session(self, request: SessionCreateRequest) -> SessionResponse:
        """Create a new interview session."""
        session_id = str(uuid.uuid4())
        
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
            question = self.question_service.get_question_by_id(assigned_question_uuid)
            if question:
                question_uuid = question.uuid
                question_text = question.question
                logger.info(f"[SESSION CREATION] ✅ Using pre-assigned question for candidate {candidate_id}")
                logger.info(f"[SESSION CREATION]    Question UUID: {question_uuid}")
                logger.info(f"[SESSION CREATION]    Question: {question_text[:100]}...")
            else:
                # Question deleted from bank, fall back to default logic
                logger.warning(f"[SESSION CREATION] ⚠️  Pre-assigned question {assigned_question_uuid} not found in question bank for candidate {candidate_id}. Using fallback.")
                assigned_question_uuid = None  # Continue with fallback logic
        
        # PRIORITY 2: Use explicit question_uuid from request (if no pre-assigned question)
        if not assigned_question_uuid:
            if request.question_uuid:
                # Fetch specific question by UUID
                logger.info(f"[SESSION CREATION] Using explicit question_uuid from request: {request.question_uuid} for candidate {candidate_id}")
                question = self.question_service.get_question_by_id(request.question_uuid)
                if question:
                    question_uuid = question.uuid
                    question_text = question.question
                    logger.info(f"[SESSION CREATION] ✅ Loaded question UUID: {question_uuid}")
                else:
                    logger.error(f"[SESSION CREATION] Question with UUID {request.question_uuid} not found for candidate {candidate_id}")
                    raise ValueError(f"Question with UUID {request.question_uuid} not found")
            elif request.tag:
                # Get random question by tag
                logger.info(f"[SESSION CREATION] Selecting random question by tag '{request.tag}' for candidate {candidate_id}")
                question = self.question_service.get_random_question_by_tag(request.tag)
                if question:
                    question_uuid = question.uuid
                    question_text = question.question
                    logger.info(f"[SESSION CREATION] ✅ Selected question UUID: {question_uuid} (tag: {request.tag})")
                else:
                    logger.error(f"[SESSION CREATION] No questions found with tag '{request.tag}' for candidate {candidate_id}")
                    raise ValueError(f"No questions found with tag: {request.tag}")
            elif not question_text:
                # Default: use URL shortener question
                logger.info(f"[SESSION CREATION] Using default question for candidate {candidate_id}")
                question = self.question_service.get_question_by_id("q1-normal-hld-url-shortener")
                if question:
                    question_uuid = question.uuid
                    question_text = question.question
                    logger.info(f"[SESSION CREATION] ✅ Using default question UUID: {question_uuid}")
                else:
                    # Fallback to hardcoded
                    logger.warning(f"[SESSION CREATION] Default question not found, using hardcoded question for candidate {candidate_id}")
                    question_text = "Design a URL shortener like bit.ly"
                    question_uuid = None
        
        question_id = question_uuid or request.question_id or "Q1"
        
        session = SessionModel(
            session_id=session_id,
            candidate_id=candidate_id,
            question_id=question_id,
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
        
        # Store question_uuid in session if available
        if question_uuid:
            session.question_id = question_uuid
        
        sessions[session_id] = session
        
        # Verify question_uuid exists in question bank before returning it
        # If it doesn't exist, return None to prevent frontend 404 errors
        final_question_uuid = question_uuid
        if question_uuid:
            # Verify the question still exists
            verify_question = self.question_service.get_question_by_id(question_uuid)
            if not verify_question:
                logger.warning(f"[SESSION CREATION] Question UUID {question_uuid} does not exist in question bank, returning None to prevent frontend errors")
                final_question_uuid = None
        
        return SessionResponse(
            session_id=session_id,
            question_text=question_text,
            question_uuid=final_question_uuid
        )
    
    def get_session(self, session_id: str, candidate_id: Optional[str] = None) -> SessionModel:
        """Get session by ID, creating if it doesn't exist."""
        if session_id not in sessions:
            # Recreate session with default question if it was lost
            # Note: candidate_id should be provided to recreate properly
            if not candidate_id:
                raise ValueError(f"Session {session_id} not found and candidate_id required to recreate")
            
            session = SessionModel(
                session_id=session_id,
                candidate_id=candidate_id,
                question_id="Q1",
                question_text="Design a URL shortener like bit.ly",
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
            sessions[session_id] = session
        
        return sessions[session_id]
    
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
    
    async def update_canvas(self, request: CanvasUpdateRequest, candidate_id: Optional[str] = None) -> CanvasUpdateResponse:
        """Handle canvas updates (save, submit, or update)."""
        session = self.get_session(request.session_id, candidate_id)
        
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
            return CanvasUpdateResponse(status="saved", version=version.version)
        
        elif request.action == "submit":
            # Evaluate figure + chat
            session.last_activity_time = time.time()
            
            latest_chat = session.chat_history[-10:] if session.chat_history else []
            chat_text = "\n".join([msg.content for msg in latest_chat])
            
            # Always fetch evaluation criteria from database using question_id
            evaluation_criteria = None
            if session.question_id:
                question = self.question_service.get_question_by_id(session.question_id)
                if question:
                    evaluation_criteria = question.evaluation_criteria
                    logger.info(f"[CANVAS SUBMIT] Using evaluation_criteria from question {session.question_id}")
                else:
                    logger.warning(f"[CANVAS SUBMIT] Question {session.question_id} not found in database")
            
            evaluation = await self.evaluator.evaluate(
                canvas_json=canvas_json,
                chat_text=chat_text,
                question_text=session.question_text,
                evaluation_criteria=evaluation_criteria
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
            
            # Format evaluation response and add to chat history
            scores_str = ", ".join([f"{k}: {v:.1f}" for k, v in evaluation.get("scores", {}).items()])
            evaluation_message = f"""Evaluation Results:

Scores: {scores_str}

Feedback: {evaluation.get('feedback', 'No feedback available')}

Follow-up Question: {evaluation.get('follow_up', 'Continue refining your design.')}"""
            
            # Add evaluation to chat history
            eval_chat_msg = ChatMessage(
                role="assistant",
                content=evaluation_message,
                timestamp=None
            )
            session.chat_history.append(eval_chat_msg)
            
            return CanvasUpdateResponse(
                status="evaluated",
                evaluation=evaluation,
                version=version.version,
                evaluation_message=evaluation_message
            )
        
        raise ValueError("Invalid action")
    
    async def send_message(self, request: ChatMessageRequest, candidate_id: Optional[str] = None) -> ChatMessageResponse:
        """Send a chat message."""
        session = self.get_session(request.session_id, candidate_id)
        
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
        
        # Check if message triggers AI response
        should_respond = self.orchestrator.should_respond(
            message=sanitized_message,
            session=session
        )
        
        if should_respond:
            # Check if user is asking to evaluate
            message_lower = sanitized_message.lower()
            is_evaluation_request = any(keyword in message_lower for keyword in [
                "evaluate", "evaluation", "review", "feedback", "assess", "analyze"
            ])
            
            # Get latest canvas - prefer canvas from request, then session, then last version
            if request.canvas_data:
                latest_canvas = request.canvas_data.model_dump()
            else:
                latest_canvas = session.current_canvas
                if not latest_canvas and session.canvas_versions:
                    latest_canvas = session.canvas_versions[-1].data
            
            # If user asks to evaluate and canvas exists, trigger full evaluation
            if is_evaluation_request and latest_canvas:
                latest_chat = session.chat_history[-10:] if session.chat_history else []
                chat_text = "\n".join([msg.content for msg in latest_chat])
                
                # Always fetch evaluation criteria from database using question_id
                evaluation_criteria = None
                if session.question_id:
                    question = self.question_service.get_question_by_id(session.question_id)
                    if question:
                        evaluation_criteria = question.evaluation_criteria
                        logger.info(f"[CHAT EVALUATION] Using evaluation_criteria from question {session.question_id}")
                    else:
                        logger.warning(f"[CHAT EVALUATION] Question {session.question_id} not found in database")
                
                evaluation = await self.evaluator.evaluate(
                    canvas_json=latest_canvas,
                    chat_text=chat_text,
                    question_text=session.question_text,
                    evaluation_criteria=evaluation_criteria
                )
                
                # Format evaluation response
                scores_str = ", ".join([f"{k}: {v:.1f}" for k, v in evaluation.get("scores", {}).items()])
                ai_response = f"""Evaluation Results:

Scores: {scores_str}

Feedback: {evaluation.get('feedback', 'No feedback available')}

Follow-up Question: {evaluation.get('follow_up', 'Continue refining your design.')}"""
                
                ai_msg = ChatMessage(
                    role="assistant",
                    content=ai_response,
                    timestamp=None
                )
                session.chat_history.append(ai_msg)
                
                return ChatMessageResponse(
                    user_message=user_msg.model_dump(),
                    ai_response=ai_response,
                    evaluation=evaluation
                )
            
            # Generate regular AI response
            try:
                ai_response = await self.orchestrator.generate_response(
                    message=sanitized_message,
                    canvas_data=latest_canvas,
                    chat_history=session.chat_history[-5:],
                    question_text=session.question_text
                )
                
                if ai_response and "API Error" in ai_response:
                    ai_response = f"I'm here to help with your system design. However, there was an issue with the API. Please check your {settings.LLM_PROVIDER.upper()}_API_KEY configuration."
                
                ai_msg = ChatMessage(
                    role="assistant",
                    content=ai_response,
                    timestamp=None
                )
                session.chat_history.append(ai_msg)
                
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
                return ChatMessageResponse(
                    user_message=user_msg.model_dump(),
                    ai_response=error_response
                )
        
        return ChatMessageResponse(user_message=user_msg.model_dump(), ai_response=None)
    
    async def check_proactive_prompts(self, session_id: str, candidate_id: Optional[str] = None) -> ProactivePromptResponse:
        """Check if any proactive prompts should be triggered."""
        session = self.get_session(session_id, candidate_id)
        
        current_time = time.time()
        
        # Adaptive polling: early return if user inactive > 60 seconds
        if session.last_activity_time:
            idle_time = current_time - session.last_activity_time
            if idle_time > 60:
                # User inactive, skip processing
                return ProactivePromptResponse(has_prompt=False, prompt=None)
        
        # Track poll time to prevent duplicate checks
        if session.last_poll_time:
            time_since_last_poll = current_time - session.last_poll_time
            if time_since_last_poll < 1:  # Less than 1 second since last poll
                return ProactivePromptResponse(has_prompt=False, prompt=None)
        
        session.last_poll_time = current_time
        
        prompt = await self.orchestrator.check_proactive_prompts(session)
        
        if prompt:
            # Check if this prompt was already added to chat history
            recent_messages = session.chat_history[-5:] if len(session.chat_history) >= 5 else session.chat_history
            prompt_already_exists = any(
                msg.role == "assistant" and msg.content == prompt 
                for msg in recent_messages
            )
            
            if not prompt_already_exists:
                # Add prompt as AI message to chat history
                ai_msg = ChatMessage(
                    role="assistant",
                    content=prompt,
                    timestamp=None
                )
                session.chat_history.append(ai_msg)
                return ProactivePromptResponse(has_prompt=True, prompt=prompt)
            else:
                return ProactivePromptResponse(has_prompt=False, prompt=None)
        
        return ProactivePromptResponse(has_prompt=False, prompt=None)
    
    def get_chat_history(self, session_id: str, candidate_id: Optional[str] = None) -> ChatHistoryResponse:
        """Get full chat history for a session."""
        session = self.get_session(session_id, candidate_id)
        return ChatHistoryResponse(messages=[msg.model_dump() for msg in session.chat_history])
    
    async def generate_final_report(self, session_id: str, candidate_id: Optional[str] = None) -> FinalReportResponse:
        """Generate final evaluation report for the session."""
        session = self.get_session(session_id, candidate_id)
        
        # Fetch evaluation_criteria from database using question_id (UUID)
        # Try to fetch question from database - question_id could be a UUID or legacy format
        evaluation_criteria = None
        if session.question_id:
            # Try fetching by UUID (question_id should be the UUID from system_design_question_bank)
            question = self.question_service.get_question_by_id(session.question_id)
            if question:
                evaluation_criteria = question.evaluation_criteria
                logger.info(f"[FINAL REPORT] ✅ Using evaluation_criteria from question {session.question_id}")
            else:
                logger.warning(f"[FINAL REPORT] ⚠️  Question {session.question_id} not found in database, will use default evaluation criteria")
        
        report = await self.evaluator.generate_final_report(session, evaluation_criteria)
        return FinalReportResponse(**report)

