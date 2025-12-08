"""
Candidate API routes for interview-related operations.
"""
import json
import logging
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_candidate
from models.candidate import Candidate
from models.test_session import TestSession
from services.interview_service import InterviewService
from schemas.mcq import MCQQuestionsResponse, SaveMCQAnswerRequest, SaveMCQAnswerResponse
from schemas.candidate import ScheduleTestRequest, ScheduleTestResponse
from schemas.admin import AssignedQuestionResponse
from schemas.test_session import (
    StartTestRequest,
    StartTestResponse,
    HeartbeatRequest,
    HeartbeatResponse,
    CompleteTestRequest,
    CompleteTestResponse,
    TestStatusResponse
)
from services.question_assignment_service import QuestionAssignmentService
from services.test_data_loader_service import TestDataLoaderService
from services.redis_sync_service import RedisSyncService
from datetime import datetime, timedelta
from utils.section_timings import start_section_timing, complete_section_timing

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidate", tags=["Candidate"])


@router.get("/{candidate_id}/mcq-questions", response_model=MCQQuestionsResponse)
async def get_mcq_questions(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get all MCQ questions for a candidate.
    
    First tries to get questions from Redis (if test data was loaded).
    Falls back to database if Redis is unavailable or data not found.
    
    Only the authenticated candidate can access their own questions.
    
    Args:
        candidate_id: UUID of the candidate
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        MCQQuestionsResponse with list of questions and their options
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs while retrieving questions
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to access another candidate's questions
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own questions."
        )
    
    # Try to get questions from Redis first
    try:
        loader_service = TestDataLoaderService(db)
        mcq_questions = loader_service.get_mcq_questions_from_redis(candidate_id)
        
        if mcq_questions:
            # Convert Redis data to response format
            from schemas.mcq import MCQQuestionResponse
            questions_list = [
                MCQQuestionResponse(
                    question_uuid=q.get("uuid"),
                    question=q.get("question"),
                    options=q.get("options", [])
                )
                for q in mcq_questions
            ]
            
            return MCQQuestionsResponse(
                success=True,
                message=f"Successfully retrieved {len(questions_list)} MCQ question(s) from Redis",
                count=len(questions_list),
                questions=questions_list
            )
    except Exception as e:
        logger.warning(f"Failed to get MCQ questions from Redis for candidate {candidate_id}: {str(e)}, falling back to database")
    
    # Fallback to database
    interview_service = InterviewService(db)
    response = interview_service.get_mcq_questions(candidate_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.post("/{candidate_id}/mcq-questions/save-answers", response_model=SaveMCQAnswerResponse)
async def save_mcq_answers(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: SaveMCQAnswerRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Save or update candidate's answers for multiple MCQ questions.
    
    This endpoint saves all candidate's selected answers for MCQ questions
    in the interview_mcq table. The answers will be stored in the candidate_answer field.
    Frontend sends a list of all questions and answers at once.
    
    Only the authenticated candidate can save their own answers.
    
    Args:
        candidate_id: UUID of the candidate
        request: SaveMCQAnswerRequest containing list of question-answer pairs
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        SaveMCQAnswerResponse with success status, counts, and failed questions
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs while saving
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to save answers for another candidate
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only save your own answers."
        )
    
    # Log the received request
    print("=== MCQ SUBMISSION REQUEST (BACKEND ROUTE) ===")
    print(f"Candidate ID: {candidate_id}")
    print(f"Number of answers received: {len(request.answers)}")
    print("Request Body:")
    print(json.dumps({
        "answers": [
            {
                "question_uuid": item.question_uuid,
                "candidate_answer": item.candidate_answer
            }
            for item in request.answers
        ]
    }, indent=2))
    print("==============================================")
    
    # SOFT SAVE: Save to Redis immediately (fast)
    try:
        from core.redis_client import get_redis_client
        from core.config import settings
        redis_client = get_redis_client()
        
        # Get existing answers from Redis (if any)
        redis_key = f"candidate:{candidate_id}:answers"
        existing_answers = redis_client.get(redis_key)
        answers_dict = json.loads(existing_answers) if existing_answers else {}
        
        # Update MCQ answers
        mcq_answers = [
            {
                "question_uuid": item.question_uuid,
                "candidate_answer": item.candidate_answer,
                "timestamp": datetime.utcnow().isoformat()
            }
            for item in request.answers
        ]
        answers_dict["mcq"] = mcq_answers
        
        # Save to Redis with TTL
        redis_client.setex(
            redis_key,
            settings.REDIS_TTL_SECONDS,
            json.dumps(answers_dict)
        )
        
        logger.info(f"Soft save to Redis successful for candidate {candidate_id}: {len(mcq_answers)} answers")
        
    except Exception as e:
        logger.warning(f"Soft save to Redis failed for candidate {candidate_id}: {str(e)}, continuing with hard save")
        # Continue with hard save even if Redis fails
    
    # HARD SAVE: Save to PostgreSQL (permanent storage)
    interview_service = InterviewService(db)
    response = interview_service.save_mcq_answers(candidate_id, request)
    
    # Update last_activity
    try:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if candidate and candidate.test_session:
            candidate.test_session.last_activity = datetime.utcnow()
            db.commit()
    except Exception as e:
        logger.warning(f"Failed to update last_activity: {str(e)}")
    
    # Return response even if some failed, but raise exception if all failed
    if response.failed_count == len(request.answers):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.post("/schedule-test", response_model=ScheduleTestResponse)
async def schedule_test(
    request: ScheduleTestRequest,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Schedule a test for the authenticated candidate.
    
    This endpoint:
    1. Saves the scheduled date and time for the candidate
    2. Updates the candidate's status to 'scheduled'
    3. Automatically assigns a system design question to the candidate
    
    Args:
        request: ScheduleTestRequest with scheduled_date (datetime)
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ScheduleTestResponse with success status and scheduled_date
        
    Raises:
        HTTPException: 
            - 400: If validation fails, candidate not found, or invalid status
            - 401: If authentication fails
            - 403: If user is not a candidate
    """
    try:
        logger.info(f"Schedule test request received for candidate {current_candidate.candidate_id}")
        logger.info(f"Request scheduled_date: {request.scheduled_date}, type: {type(request.scheduled_date)}")
        logger.info(f"Current candidate status: {current_candidate.status}")
        
        interview_service = InterviewService(db)
        response = await interview_service.save_test_schedule(current_candidate.candidate_id, request)
        
        if not response.success:
            logger.warning(f"Schedule test failed for candidate {current_candidate.candidate_id}: {response.message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.message
            )
        
        logger.info(f"Schedule test successful for candidate {current_candidate.candidate_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in schedule_test: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{candidate_id}/assigned-question", response_model=AssignedQuestionResponse)
async def get_assigned_question(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get the assigned system design question for a candidate.
    
    Only accessible when the test is in progress (status = 'in progress').
    This endpoint can only be accessed during an active test session.
    
    Args:
        candidate_id: Candidate UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        AssignedQuestionResponse with question details
        
    Raises:
        HTTPException: 
            - 403: If user is not a candidate, tries to access another candidate's question, or test is not in progress
            - 404: If candidate not found or no question assigned
            - 401: If authentication fails
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own assigned question."
        )
    
    # Check if test is in progress (status must be 'in progress')
    candidate_status = current_candidate.status.lower() if current_candidate.status else None
    
    if candidate_status != 'in progress':
        if candidate_status in ['shortlisted', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has not started yet. The assigned question is only available during the test."
            )
        elif candidate_status == 'scheduled':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has not started yet. The assigned question is only available during the test."
            )
        elif candidate_status in ['completed', 'selected', 'not selected']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has been completed. The assigned question is no longer available."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test is not in progress. The assigned question is only available during an active test session."
            )
    
    assignment_service = QuestionAssignmentService(db)
    question_details = assignment_service.get_assigned_question_details(candidate_id)
    
    if not question_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No question assigned to this candidate or candidate not found"
        )
    
    return AssignedQuestionResponse(**question_details)


@router.post("/{candidate_id}/test/start", response_model=StartTestResponse)
async def start_test(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: StartTestRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Start a test session for a candidate.
    
    Creates or resumes a test session, records test start time, and updates
    candidate status to 'in progress'. Returns session details and remaining time.
    
    Only the authenticated candidate can start their own test.
    
    Args:
        candidate_id: UUID of the candidate
        request: StartTestRequest with optional duration_minutes
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        StartTestResponse with session details and remaining time
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to start another candidate's test
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only start your own test."
        )
    
    try:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Get or create test session - query directly to avoid relationship issues
        test_session = db.query(TestSession).filter(TestSession.candidate_id == candidate_id).first()
        
        # Check if test is already active
        if candidate.status == 'in progress' and test_session and test_session.test_start_time:
            # Calculate remaining time
            elapsed = datetime.utcnow() - test_session.test_start_time
            remaining = timedelta(minutes=test_session.test_duration_minutes or request.duration_minutes) - elapsed
            remaining_seconds = max(0, int(remaining.total_seconds()))
            
            return StartTestResponse(
                success=True,
                message="Test session already exists",
                test_start_time=test_session.test_start_time,
                remaining_seconds=remaining_seconds
            )
        
        # Start new test session - set all fields BEFORE creating/committing
        now = datetime.utcnow()
        
        if not test_session:
            # Create new test session with all required fields set
            test_session = TestSession(
                candidate_id=candidate_id,
                test_start_time=now,  # ✅ Set before any database operation
                test_duration_minutes=request.duration_minutes,
                last_activity=now,
                last_heartbeat=now,
                completion_method=None,
                test_completed_at=None,
                sections_completed={},
                pending_answers={},
                section_timings={}
            )
            db.add(test_session)
        else:
            # Update existing test session
            test_session.test_start_time = now
            test_session.test_duration_minutes = request.duration_minutes
            test_session.last_activity = now
            test_session.last_heartbeat = now
            test_session.completion_method = None
            test_session.test_completed_at = None
            test_session.sections_completed = {}
            test_session.pending_answers = {}
            test_session.section_timings = {}
        
        candidate.status = 'in progress'
        
        db.commit()  # ✅ Now commit with all fields set
        
        # Load all test data (MCQ, Coding, System Design) into Redis
        try:
            loader_service = TestDataLoaderService(db)
            load_result = loader_service.load_test_data_to_redis(candidate_id)
            
            if not load_result.get("success"):
                logger.warning(f"Failed to load test data to Redis for candidate {candidate_id}: {load_result.get('error')}")
                # Continue anyway - Redis is optional, can fallback to DB
        except Exception as e:
            logger.error(f"Error loading test data to Redis for candidate {candidate_id}: {str(e)}")
            # Continue anyway - Redis is optional, can fallback to DB
        
        return StartTestResponse(
            success=True,
            message="Test session created successfully",
            test_start_time=now,
            remaining_seconds=request.duration_minutes * 60
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error starting test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to start test: {str(e)}"
        )


@router.post("/{candidate_id}/test/heartbeat", response_model=HeartbeatResponse)
async def update_heartbeat(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: HeartbeatRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Update heartbeat timestamp for a test session.
    
    This endpoint updates the last_heartbeat in both Redis (soft save) and PostgreSQL (hard save).
    Returns server timestamp for timer sync.
    
    Heartbeat is sent every 2 minutes to track candidate activity.
    If heartbeat stops for 5+ minutes, background job will auto-complete the test.
    
    Only the authenticated candidate can update their own heartbeat.
    
    Args:
        candidate_id: UUID of the candidate
        request: HeartbeatRequest with optional client_timestamp
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        HeartbeatResponse with server timestamp and remaining time
        
    Raises:
        HTTPException: 
            - 400: If no active test session found
            - 401: If authentication fails
            - 403: If user is not a candidate
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only update your own heartbeat."
        )
    
    try:
        candidate = db.query(Candidate).filter(
            Candidate.candidate_id == candidate_id,
            Candidate.status == 'in progress'
        ).first()
        
        if not candidate or not candidate.test_session or not candidate.test_session.test_start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active test session found"
            )
        
        test_session = candidate.test_session
        now = datetime.utcnow()
        
        # SOFT SAVE: Update Redis heartbeat (fast)
        try:
            from core.redis_client import get_redis_client
            from core.config import settings
            redis_client = get_redis_client()
            
            redis_key = f"candidate:{candidate_id}:heartbeat"
            redis_client.setex(
                redis_key,
                300,  # 5 minute TTL
                now.isoformat()
            )
        except Exception as e:
            logger.warning(f"Failed to update heartbeat in Redis for candidate {candidate_id}: {str(e)}")
            # Continue with PostgreSQL update
        
        # HARD SAVE: Update PostgreSQL heartbeat (permanent)
        test_session.last_heartbeat = now
        test_session.last_activity = now
        db.commit()
        
        # Calculate remaining time
        elapsed = now - test_session.test_start_time
        remaining = timedelta(minutes=test_session.test_duration_minutes or 60) - elapsed
        remaining_seconds = max(0, int(remaining.total_seconds()))
        
        return HeartbeatResponse(
            success=True,
            message="Heartbeat updated",
            server_timestamp=now,
            remaining_seconds=remaining_seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error updating heartbeat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error updating heartbeat: {str(e)}"
        )


@router.post("/{candidate_id}/test/complete", response_model=CompleteTestResponse)
async def complete_test(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: CompleteTestRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Complete a test session and save all answers.
    
    Unified endpoint for all completion methods:
    - 'manual': User clicks submit button
    - 'tab_close': Browser tab closed (via sendBeacon)
    - 'timer_expired': Test timer reached zero
    - 'heartbeat_timeout': Reserved for future use (not currently implemented)
    - 'auto': Automatic completion by backend
    
    This endpoint saves all candidate answers (MCQ, Coding, System Design),
    marks the test session as completed, and updates candidate status.
    The endpoint is idempotent - safe to call multiple times.
    
    Supports two MCQ answer formats:
    1. Full format: SaveMCQAnswerRequest object (for regular API calls)
    2. Simplified format: List[Dict[str, str]] (for sendBeacon/tab close)
    
    Only the authenticated candidate can complete their own test.
    
    Args:
        candidate_id: UUID of the candidate
        request: CompleteTestRequest with all answers and completion_method
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        CompleteTestResponse with completion confirmation
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to complete another candidate's test
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only complete your own test."
        )
    
    # Get completion_method from request body (defaults to 'manual' if not provided)
    completion_method = request.completion_method or "manual"
    
    # Validate completion_method
    valid_methods = ['manual', 'tab_close', 'timer_expired', 'heartbeat_timeout', 'auto']
    if completion_method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid completion_method. Must be one of: {', '.join(valid_methods)}"
        )
    
    try:
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Check if already completed
        if candidate.status == 'completed':
            completed_at = candidate.test_session.test_completed_at if candidate.test_session else None
            return CompleteTestResponse(
                success=True,
                message="Test already completed",
                completed_at=completed_at
            )
        
        # Handle MCQ answers - support both full and simplified formats
        mcq_request = None
        if request.mcq_answers:
            # Check if it's simplified format (List[Dict])
            if isinstance(request.mcq_answers, list):
                # Convert simplified format to SaveMCQAnswerRequest
                from schemas.mcq import MCQAnswerItem
                mcq_items = [
                    MCQAnswerItem(
                        question_uuid=item.get("question_uuid", ""),
                        candidate_answer=item.get("candidate_answer", "")
                    )
                    for item in request.mcq_answers
                    if isinstance(item, dict) and item.get("question_uuid") and item.get("candidate_answer")
                ]
                if mcq_items:
                    mcq_request = SaveMCQAnswerRequest(answers=mcq_items)
            # Check if it's dict format (serialized SaveMCQAnswerRequest)
            elif isinstance(request.mcq_answers, dict):
                if "answers" in request.mcq_answers:
                    # Handle dict format that might be serialized SaveMCQAnswerRequest
                    from schemas.mcq import MCQAnswerItem
                    mcq_items = [
                        MCQAnswerItem(**item) if isinstance(item, dict) else item
                        for item in request.mcq_answers.get("answers", [])
                    ]
                    if mcq_items:
                        mcq_request = SaveMCQAnswerRequest(answers=mcq_items)
                else:
                    # Single dict item, convert to list format
                    from schemas.mcq import MCQAnswerItem
                    if request.mcq_answers.get("question_uuid") and request.mcq_answers.get("candidate_answer"):
                        mcq_request = SaveMCQAnswerRequest(answers=[MCQAnswerItem(**request.mcq_answers)])
            else:
                # Assume it's already SaveMCQAnswerRequest object (Pydantic model)
                # Check if it has answers attribute
                if hasattr(request.mcq_answers, 'answers'):
                    mcq_request = request.mcq_answers
                else:
                    logger.warning(f"Unknown MCQ answers format: {type(request.mcq_answers)}")
        
        # Get all answers from Redis first (source of truth)
        sync_service = RedisSyncService(db)
        redis_answers = sync_service.get_answers_from_redis(candidate_id)
        redis_progress = sync_service.get_progress_from_redis(candidate_id)
        
        # Merge Redis data with request data (Redis takes priority if both exist)
        # If request has new answers, they will be saved to Redis first, then synced
        
        # Save MCQ answers if provided in request
        if mcq_request and mcq_request.answers:
            # Save to Redis first (soft save)
            try:
                from core.redis_client import get_redis_client
                from core.config import settings
                redis_client = get_redis_client()
                
                redis_key = f"candidate:{candidate_id}:answers"
                existing_answers = redis_client.get(redis_key)
                answers_dict = json.loads(existing_answers) if existing_answers else {}
                
                mcq_answers = [
                    {
                        "question_uuid": item.question_uuid,
                        "candidate_answer": item.candidate_answer,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    for item in mcq_request.answers
                ]
                answers_dict["mcq"] = mcq_answers
                
                redis_client.setex(
                    redis_key,
                    settings.REDIS_TTL_SECONDS,
                    json.dumps(answers_dict)
                )
            except Exception as e:
                logger.warning(f"Failed to save MCQ answers to Redis: {str(e)}")
            
            # Save to PostgreSQL (hard save)
            interview_service = InterviewService(db)
            mcq_response = interview_service.save_mcq_answers(candidate_id, mcq_request)
            if not mcq_response.success:
                logger.warning(f"Some MCQ answers failed to save: {mcq_response.message}")
        
        # Sync all remaining data from Redis to PostgreSQL (final hard save)
        sync_result = sync_service.sync_all_answers_to_postgresql(candidate_id)
        if not sync_result.get("success"):
            logger.warning(f"Some data failed to sync from Redis: {sync_result.get('error')}")
        
        # TODO: Save coding answers if provided
        # TODO: Save system design answers if provided
        
        # Update candidate test completion
        now = datetime.utcnow()
        candidate.status = 'completed'
        
        # Get or create test session
        test_session = candidate.test_session
        if not test_session:
            test_session = TestSession(candidate_id=candidate_id)
            db.add(test_session)
            db.flush()
        
        test_session.completion_method = completion_method
        test_session.test_completed_at = now
        
        # Use sections_completed from Redis if available, otherwise from request
        if redis_progress.get("sections_completed"):
            test_session.sections_completed = redis_progress["sections_completed"]
        else:
            test_session.sections_completed = request.sections_completed or {}
        
        # Use section_timings from Redis if available
        if redis_progress.get("section_timings"):
            test_session.section_timings = redis_progress["section_timings"]
        
        test_session.pending_answers = None  # Clear pending answers after completion
        
        db.commit()
        
        # Clear Redis keys after successful completion
        try:
            loader_service = TestDataLoaderService(db)
            loader_service.clear_test_data_from_redis(candidate_id)
        except Exception as e:
            logger.warning(f"Failed to clear Redis keys for candidate {candidate_id}: {str(e)}")
        
        return CompleteTestResponse(
            success=True,
            message="Test completed successfully",
            completed_at=now
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing test: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to complete test: {str(e)}"
        )


@router.get("/{candidate_id}/test/status", response_model=TestStatusResponse)
async def get_test_status(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get current test status for a candidate.
    
    Returns test session status, remaining time, sections completed,
    and last activity timestamp. Used for page reload/recovery.
    
    Only the authenticated candidate can view their own test status.
    
    Args:
        candidate_id: UUID of the candidate
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        TestStatusResponse with current test status
        
    Raises:
        HTTPException: 
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to access another candidate's status
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own test status."
        )
    
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    
    if not candidate or not candidate.test_session or not candidate.test_session.test_start_time:
        return TestStatusResponse(
            success=False,
            message="No test session found",
            status=None,
            remaining_seconds=0,
            sections_completed={},
            last_activity=None
        )
    
    test_session = candidate.test_session
    
    # Calculate remaining time
    if candidate.status == 'in progress' and test_session.test_start_time:
        elapsed = datetime.utcnow() - test_session.test_start_time
        remaining = timedelta(minutes=test_session.test_duration_minutes or 60) - elapsed
        remaining_seconds = max(0, int(remaining.total_seconds()))
    else:
        remaining_seconds = 0
    
    # Determine status
    if candidate.status == 'in progress':
        test_status = 'active'
    elif candidate.status == 'completed':
        test_status = 'completed'
    else:
        test_status = None
    
    return TestStatusResponse(
        success=True,
        message="Test session found",
        status=test_status,
        remaining_seconds=remaining_seconds,
        sections_completed=test_session.sections_completed or {},
        last_activity=test_session.last_activity
    )

