"""
Candidate API routes for interview-related operations.
"""
import json
import logging
import random
import time
import httpx
from fastapi import APIRouter, Depends, HTTPException, status, Path, Query
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_candidate
from core.config import settings
from models.candidate import Candidate
from models.test_session import TestSession
from models.coding_question_bank import CodingQuestionBank
from models.interview_coding import InterviewCoding
from services.interview_service import InterviewService
from schemas.mcq import MCQQuestionsResponse, SaveMCQAnswerRequest, SaveMCQAnswerResponse
from schemas.candidate import ScheduleTestRequest, ScheduleTestResponse, GetScheduledDateResponse, InterviewSummaryResponse
from schemas.admin import AssignedQuestionResponse
from schemas.coding import RunCodeRequest, RunCodeResponse, SubmitCodingAnswerRequest, SubmitCodingAnswerResponse, CodingQuestionsResponse, CodingQuestionResponse, FinalizeCodingSectionResponse
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
from datetime import datetime, timedelta, timezone
from utils.section_timings import start_section_timing, complete_section_timing
from core.scheduler_manager import start_scheduler_jobs, stop_scheduler_jobs_if_no_active_tests

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
    
    Only accessible when the test is in progress (status = 'in progress').
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
            - 403: If user is not a candidate, tries to access another candidate's questions, or test is not in progress
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own questions."
        )
    
    # Check if test is in progress (status must be 'in progress')
    candidate_status = current_candidate.status.lower() if current_candidate.status else None
    
    if candidate_status != 'in progress':
        if candidate_status in ['shortlisted', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has not started yet. The assigned questions are only available during the test."
            )
        elif candidate_status == 'scheduled':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has not started yet. The assigned questions are only available during the test."
            )
        elif candidate_status in ['completed', 'selected', 'not selected']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has been completed. The assigned questions are no longer available."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test is not in progress. The assigned questions are only available during an active test session."
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
            
            # Shuffle the questions to randomize their order
            random.shuffle(questions_list)
            
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


@router.get("/{candidate_id}/coding-questions", response_model=CodingQuestionsResponse)
async def get_coding_questions(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get all coding questions for a candidate.
    
    First tries to get questions from Redis (if test data was loaded).
    Falls back to database if Redis is unavailable or data not found.
    
    Only accessible when the test is in progress (status = 'in progress').
    Only the authenticated candidate can access their own questions.
    
    Args:
        candidate_id: UUID of the candidate
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        CodingQuestionsResponse with list of questions, test cases, and boilerplate code
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs while retrieving questions
            - 401: If authentication fails
            - 403: If user is not a candidate, tries to access another candidate's questions, or test is not in progress
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own questions."
        )
    
    # Check if test is in progress (status must be 'in progress')
    candidate_status = current_candidate.status.lower() if current_candidate.status else None
    
    if candidate_status != 'in progress':
        if candidate_status in ['shortlisted', 'rejected']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has not started yet. The assigned questions are only available during the test."
            )
        elif candidate_status == 'scheduled':
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has not started yet. The assigned questions are only available during the test."
            )
        elif candidate_status in ['completed', 'selected', 'not selected']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test has been completed. The assigned questions are no longer available."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Test is not in progress. The assigned questions are only available during an active test session."
            )
    
    # Try to get questions from Redis first
    try:
        loader_service = TestDataLoaderService(db)
        coding_questions = loader_service.get_coding_questions_from_redis(candidate_id)
        
        if coding_questions:
            # Convert Redis data to response format
            questions_list = [
                CodingQuestionResponse(
                    question_uuid=q.get("question_uuid"),
                    question=q.get("question"),
                    sample_test_cases=q.get("sample_test_cases", []),
                    boilerplate_code=q.get("boilerplate_code")
                )
                for q in coding_questions
            ]
            
            return CodingQuestionsResponse(
                success=True,
                message=f"Successfully retrieved {len(questions_list)} coding question(s) from Redis",
                count=len(questions_list),
                questions=questions_list
            )
    except Exception as e:
        logger.warning(f"Failed to get coding questions from Redis for candidate {candidate_id}: {str(e)}, falling back to database")
    
    # Fallback to database
    try:
        # Get all coding question assignments for this candidate
        coding_records = db.query(InterviewCoding).filter(
            InterviewCoding.candidate_id == candidate_id
        ).all()
        
        if not coding_records:
            return CodingQuestionsResponse(
                success=True,
                message="No coding questions assigned to this candidate",
                count=0,
                questions=[]
            )
        
        # Fetch question details from CodingQuestionBank
        questions_list = []
        for coding in coding_records:
            coding_question = None
            if hasattr(coding, 'question') and coding.question:
                coding_question = coding.question
            elif hasattr(coding, 'question_uuid'):
                coding_question = db.query(CodingQuestionBank).filter(
                    CodingQuestionBank.uuid == coding.question_uuid
                ).first()
            
            if coding_question:
                questions_list.append(
                    CodingQuestionResponse(
                        question_uuid=coding.question_uuid,
                        question=coding_question.question if hasattr(coding_question, 'question') else "",
                        sample_test_cases=coding_question.sample_test_cases if hasattr(coding_question, 'sample_test_cases') and coding_question.sample_test_cases else [],
                        boilerplate_code=coding_question.boiler_plate if hasattr(coding_question, 'boiler_plate') else None
                    )
                )
        
        return CodingQuestionsResponse(
            success=True,
            message=f"Successfully retrieved {len(questions_list)} coding question(s) from database",
            count=len(questions_list),
            questions=questions_list
        )
        
    except Exception as e:
        logger.error(f"Error retrieving coding questions from database for candidate {candidate_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to retrieve coding questions: {str(e)}"
        )


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
    candidate_id: str = Query(..., description="Candidate UUID from invitation link", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: ScheduleTestRequest = ...,
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
        candidate_id: Candidate UUID from invitation link (REQUIRED)
        request: ScheduleTestRequest with scheduled_date (datetime)
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        ScheduleTestResponse with success status and scheduled_date
        
    Raises:
        HTTPException: 
            - 400: If validation fails, candidate not found, or invalid status
            - 401: If authentication fails
            - 403: If user is not a candidate or candidate_id mismatch
    """
    try:
        logger.info(f"Schedule test request received for candidate {candidate_id}")
        logger.info(f"Request scheduled_date: {request.scheduled_date}, type: {type(request.scheduled_date)}")
        logger.info(f"Current candidate status: {current_candidate.status}")
        
        # Verify that the candidate_id from query matches the authenticated candidate
        if current_candidate.candidate_id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Candidate ID does not match authenticated candidate."
            )
        
        interview_service = InterviewService(db)
        response = await interview_service.save_test_schedule(candidate_id, request)
        
        if not response.success:
            logger.warning(f"Schedule test failed for candidate {candidate_id}: {response.message}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=response.message
            )
        
        logger.info(f"Schedule test successful for candidate {candidate_id}")
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in schedule_test: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/{candidate_id}/scheduled-date", response_model=GetScheduledDateResponse)
async def get_scheduled_date(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get the scheduled date for a candidate.
    
    Returns the scheduled_date stored in the database for the candidate.
    The date is returned in ISO format with timezone information preserved.
    
    Args:
        candidate_id: Candidate UUID
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        GetScheduledDateResponse with scheduled_date in ISO format
        
    Raises:
        HTTPException:
            - 403: If candidate_id doesn't match authenticated candidate
            - 404: If candidate not found
    """
    try:
        # Verify that the candidate_id matches the authenticated candidate
        if current_candidate.candidate_id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Candidate ID does not match authenticated candidate."
            )
        
        # Fetch candidate from database to get the latest scheduled_date
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Return scheduled_date in ISO format with IST timezone
        if candidate.scheduled_date:
            # scheduled_date is stored as naive IST time (not UTC)
            # If timezone-naive, treat it as IST time
            ist_timezone = timezone(timedelta(hours=5, minutes=30))
            if candidate.scheduled_date.tzinfo is None:
                # Treat naive datetime as IST time
                ist_datetime = candidate.scheduled_date.replace(tzinfo=ist_timezone)
            else:
                # If timezone-aware, convert to IST
                ist_datetime = candidate.scheduled_date.astimezone(ist_timezone)
            
            # Return in ISO format with IST timezone
            scheduled_date_iso = ist_datetime.isoformat()
            return GetScheduledDateResponse(
                success=True,
                message="Scheduled date retrieved successfully",
                scheduled_date=scheduled_date_iso
            )
        else:
            return GetScheduledDateResponse(
                success=True,
                message="No scheduled date found for this candidate",
                scheduled_date=None
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in get_scheduled_date: {str(e)}", exc_info=True)
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
    
    First tries to get question from Redis (if test data was loaded).
    Falls back to database if Redis is unavailable or data not found.
    
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
    
    # Try to get question from Redis first
    try:
        loader_service = TestDataLoaderService(db)
        redis_question = loader_service.get_system_design_question_from_redis(candidate_id)
        
        if redis_question:
            # Convert Redis data to response format
            return AssignedQuestionResponse(
                candidate_id=candidate_id,
                question_uuid=redis_question.get("question_uuid"),
                question=redis_question.get("question")
            )
    except Exception as e:
        logger.warning(f"Failed to get system design question from Redis for candidate {candidate_id}: {str(e)}, falling back to database")
    
    # Fallback to database
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
        
        # Update scheduled_date to current time when test starts (regardless of what was scheduled)
        candidate.scheduled_date = now
        
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
        
        # Start scheduler jobs when test begins
        start_scheduler_jobs()
        
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
        
        # Query test_session directly to avoid relationship issues (InstrumentedList)
        test_session = db.query(TestSession).filter(TestSession.candidate_id == candidate_id).first()
        
        if not candidate or not test_session or not test_session.test_start_time:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active test session found"
            )
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
        remaining = timedelta(minutes=test_session.test_duration_minutes or 180) - elapsed
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
    # Log the complete test request received
    logger.info(f"[COMPLETE TEST] Received complete test request for candidate {candidate_id}")
    logger.info(f"[COMPLETE TEST] Completion method: {request.completion_method}")
    logger.info(f"[COMPLETE TEST] Section timings in request: {request.section_timings}")
    logger.info(f"[COMPLETE TEST] Sections completed: {request.sections_completed}")
    if request.mcq_answers:
        if isinstance(request.mcq_answers, list):
            logger.info(f"[COMPLETE TEST] MCQ answers count (simplified format): {len(request.mcq_answers)}")
        elif hasattr(request.mcq_answers, 'answers'):
            logger.info(f"[COMPLETE TEST] MCQ answers count: {len(request.mcq_answers.answers)}")
        else:
            logger.info(f"[COMPLETE TEST] MCQ answers format: {type(request.mcq_answers)}")
    logger.info(f"[COMPLETE TEST] Integrity metrics: {request.integrity}")
    print(f"[COMPLETE TEST] Integrity metrics: {request.integrity}")
    
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
        
        # ============================================================================
        # SAVE ANY PENDING MCQ ANSWERS (if provided in request)
        # ============================================================================
        # Save to Redis and PostgreSQL, but don't analyze yet
        # The ensure_all_analyses_complete() method will handle analysis
        if mcq_request and mcq_request.answers:
            logger.info(f"[TEST_COMPLETION] Saving pending MCQ answers for candidate {candidate_id}")
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
            
            # Save to PostgreSQL (hard save) - analysis will be handled separately
            interview_service = InterviewService(db)
            # Temporarily disable analysis in save_mcq_answers by catching any errors
            try:
                mcq_response = interview_service.save_mcq_answers(candidate_id, mcq_request)
                if not mcq_response.success:
                    logger.warning(f"Some MCQ answers failed to save: {mcq_response.message}")
            except Exception as e:
                logger.warning(f"Failed to save MCQ answers to PostgreSQL: {str(e)}")
        
        # ============================================================================
        # ENSURE ALL SECTION ANALYSES ARE COMPLETE
        # ============================================================================
        # This intelligently checks each section and only analyzes if needed
        # Prevents duplicate analysis and ensures all data is ready for email
        logger.info(f"[TEST_COMPLETION] Ensuring all analyses are complete for candidate {candidate_id}")
        
        interview_service = InterviewService(db)
        analysis_result = interview_service.ensure_all_analyses_complete(candidate_id)
        
        if analysis_result["completed_analyses"]:
            logger.info(f"[TEST_COMPLETION] ✅ Completed analyses: {', '.join(analysis_result['completed_analyses'])}")
        if analysis_result["skipped_analyses"]:
            logger.info(f"[TEST_COMPLETION] ⏭️  Skipped analyses (already done): {', '.join(analysis_result['skipped_analyses'])}")
        if analysis_result["failed_analyses"]:
            logger.warning(f"[TEST_COMPLETION] ❌ Failed analyses: {analysis_result['failed_analyses']}")
        
        # ============================================================================
        # SYNC ALL REMAINING DATA FROM REDIS TO POSTGRESQL
        # ============================================================================
        # Final hard save of any remaining data
        sync_result = sync_service.sync_all_answers_to_postgresql(candidate_id)
        if not sync_result.get("success"):
            logger.warning(f"Some data failed to sync from Redis: {sync_result.get('error')}")
        
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
        
        # Use section_timings from request if available, otherwise from Redis
        logger.info(f"[COMPLETE TEST] Section timings received from request: {request.section_timings}")
        logger.info(f"[COMPLETE TEST] Section timings from Redis: {redis_progress.get('section_timings')}")
        if request.section_timings:
            test_session.section_timings = request.section_timings
            logger.info(f"[COMPLETE TEST] Storing section_timings from request: {request.section_timings}")
        elif redis_progress.get("section_timings"):
            test_session.section_timings = redis_progress["section_timings"]
            logger.info(f"[COMPLETE TEST] Storing section_timings from Redis: {redis_progress.get('section_timings')}")
        else:
            logger.warning(f"[COMPLETE TEST] No section_timings found in request or Redis for candidate {candidate_id}")
        
        test_session.pending_answers = None  # Clear pending answers after completion
        
        # ============================================================================
        # UPDATE CHEAT METRICS (before commit to ensure it's part of the transaction)
        # ============================================================================
        # Update cheat metrics in interview_analysis_table from integrity data
        if request.integrity:
            try:
                logger.info(f"[TEST_COMPLETION] Updating cheat metrics for candidate {candidate_id}: {request.integrity}")
                interview_service._update_cheat_metrics(candidate_id, request.integrity)
                logger.info(f"[TEST_COMPLETION] ✅ Updated cheat metrics for candidate {candidate_id}")
            except Exception as e:
                # Log full error details but don't fail test completion
                logger.error(f"Failed to update cheat metrics for candidate {candidate_id}: {str(e)}", exc_info=True)
                # Continue - cheat metrics update failure shouldn't block test completion
        
        # Commit all changes (test session, cheat metrics, section timings) together
        try:
            db.commit()
            logger.info(f"[TEST_COMPLETION] ✅ Successfully committed test completion data for candidate {candidate_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit test completion data for candidate {candidate_id}: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to save test completion data: {str(e)}"
            )
        
        # Check if we should stop scheduler jobs (only if no other active tests)
        stop_scheduler_jobs_if_no_active_tests()
        
        # Clear Redis keys after successful completion
        try:
            loader_service = TestDataLoaderService(db)
            loader_service.clear_test_data_from_redis(candidate_id)
        except Exception as e:
            logger.warning(f"Failed to clear Redis keys for candidate {candidate_id}: {str(e)}")
        
        # Send assessment report email asynchronously (non-blocking)
        try:
            import threading
            import asyncio
            from services.email_service import email_service
            
            def send_email_async():
                """Helper function to run async email sending in background thread."""
                try:
                    # Create a new database session for the email thread
                    db_gen = get_db()
                    db_email = next(db_gen)
                    try:
                        asyncio.run(
                            email_service.send_assessment_report_email(
                                candidate_id=candidate_id,
                                candidate_email=candidate.email_id,
                                candidate_name=candidate.name,
                                completion_date=now,
                                db=db_email
                            )
                        )
                    finally:
                        db_email.close()
                except Exception as e:
                    logger.error(f"Error in background email thread for candidate {candidate_id}: {str(e)}", exc_info=True)
            
            # Start email sending in background thread
            email_thread = threading.Thread(target=send_email_async, daemon=True)
            email_thread.start()
            
            logger.info(f"Assessment report email queued for candidate {candidate_id}")
        except Exception as e:
            # Don't fail test completion if email fails
            logger.error(f"Failed to queue assessment report email for candidate {candidate_id}: {str(e)}", exc_info=True)
        
        # Generate interview summary asynchronously (non-blocking)
        # Run in background thread to avoid blocking test completion
        try:
            import threading
            import asyncio
            
            def generate_summary_async():
                """Helper function to run async summary generation in background thread."""
                try:
                    # Create new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    # Create new database session for background task
                    from core.database import SessionLocal
                    background_db = SessionLocal()
                    try:
                        background_interview_service = InterviewService(background_db)
                        loop.run_until_complete(
                            background_interview_service.generate_and_save_interview_summary(candidate_id)
                        )
                    finally:
                        background_db.close()
                        loop.close()
                except Exception as e:
                    logger.error(f"Error in background summary generation thread: {str(e)}")
            
            # Start summary generation in background thread
            summary_thread = threading.Thread(target=generate_summary_async, daemon=True)
            summary_thread.start()
            logger.info(f"Started background summary generation for candidate {candidate_id}")
        except Exception as e:
            logger.warning(f"Failed to start summary generation for candidate {candidate_id}: {str(e)}")
            # Continue - summary generation is non-critical
        
        return CompleteTestResponse(
            success=True,
            message="Test completed successfully",
            completed_at=now
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error completing test for candidate {candidate_id}: {str(e)}", exc_info=True)
        logger.error(f"Request data - completion_method: {request.completion_method if request else 'N/A'}, "
                    f"has_integrity: {bool(request.integrity) if request else False}, "
                    f"has_section_timings: {bool(request.section_timings) if request else False}")
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
    
    # Query test_session directly to avoid relationship issues (InstrumentedList)
    test_session = db.query(TestSession).filter(TestSession.candidate_id == candidate_id).first()
    
    if not candidate or not test_session or not test_session.test_start_time:
        return TestStatusResponse(
            success=False,
            message="No test session found",
            status=None,
            remaining_seconds=0,
            sections_completed={},
            last_activity=None
        )
    
    # Calculate remaining time
    if candidate.status == 'in progress' and test_session.test_start_time:
        elapsed = datetime.utcnow() - test_session.test_start_time
        remaining = timedelta(minutes=test_session.test_duration_minutes or 180) - elapsed
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


@router.post("/{candidate_id}/coding/run", response_model=RunCodeResponse)
async def run_code(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: RunCodeRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Run code against test cases for a coding question.
    
    Supports two modes:
    - "run": Execute only sample test cases (safe to show results)
    - "run_all": Execute sample test cases + hidden test cases (results sanitized)
    
    Test cases are fetched from Redis (if available) or database.
    Code is executed via external execution service.
    
    Only the authenticated candidate can run code for their own questions.
    
    Args:
        candidate_id: UUID of the candidate
        request: RunCodeRequest with question_id, language, code, and mode
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        RunCodeResponse with execution results
        
    Raises:
        HTTPException: 
            - 400: If validation fails or question not found
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to access another candidate's questions
            - 502: If execution service returns invalid response
            - 503: If execution service is unavailable
            - 504: If execution service times out
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only run code for your own questions."
        )
    
    try:
        # Measure total endpoint processing time
        endpoint_start_time = time.perf_counter()
        preprocessing_start_time = time.perf_counter()
        
        loader_service = TestDataLoaderService(db)
        sample_test_cases = []
        test_cases = []
        
        # Step 1: Get question from database (test_cases are not cached in Redis due to size)
        coding_question_db = db.query(CodingQuestionBank).filter(
            CodingQuestionBank.uuid == request.question_id
        ).first()
        
        if not coding_question_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Coding question with ID {request.question_id} not found"
            )
        
        # Extract test cases from database
        sample_test_cases = coding_question_db.sample_test_cases if coding_question_db.sample_test_cases else []
        test_cases = coding_question_db.test_cases if coding_question_db.test_cases else []
        
        # Step 3: Validate test cases exist
        if not sample_test_cases and not test_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No test cases found for this question"
            )
        
        if request.mode == "run" and not sample_test_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No sample test cases found for this question"
            )
        
        # Step 4: Format test cases for execution service
        # Build formatted test cases based on mode
        formatted_test_cases = []
        
        if request.mode == "run":
            # For "run" mode: use only sample_test_cases
            if sample_test_cases:
                for idx, tc in enumerate(sample_test_cases):
                    if isinstance(tc, dict):
                        formatted_tc = {
                            "id": tc.get("id", f"sample_{idx + 1}"),
                            "input": tc.get("input", ""),
                            "expected_output": tc.get("expected_output", "")
                        }
                        formatted_test_cases.append(formatted_tc)
        elif request.mode == "run_all":
            # For "run_all" mode: combine sample_test_cases + test_cases
            # First add sample test cases
            if sample_test_cases:
                for idx, tc in enumerate(sample_test_cases):
                    if isinstance(tc, dict):
                        formatted_tc = {
                            "id": tc.get("id", f"sample_{idx + 1}"),
                            "input": tc.get("input", ""),
                            "expected_output": tc.get("expected_output", "")
                        }
                        formatted_test_cases.append(formatted_tc)
            # Then add hidden test cases
            if test_cases:
                for idx, tc in enumerate(test_cases):
                    if isinstance(tc, dict):
                        formatted_tc = {
                            "id": tc.get("id", f"hidden_{idx + 1}"),
                            "input": tc.get("input", ""),
                            "expected_output": tc.get("expected_output", "")
                        }
                        formatted_test_cases.append(formatted_tc)
        
        # Step 5: Build request for execution service
        execution_request = {
            "language": request.language,
            "code": request.code,
            "test_cases": formatted_test_cases,
            "user_id": candidate_id,
            "question_id": request.question_id
        }
        
        preprocessing_end_time = time.perf_counter()
        preprocessing_duration_ms = (preprocessing_end_time - preprocessing_start_time) * 1000
        
        # Step 6: Call external execution service
        execution_url = settings.CODE_EXECUTION_URL
        
        # Measure execution time
        execution_start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    execution_url,
                    json=execution_request,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                execution_result = response.json()
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            
            # Print and log execution time with breakdown
            print(f"⏱️  Execution Service Response Time: {execution_duration_ms:.2f}ms (Question: {request.question_id})")
            print(f"   📊 Preprocessing Time (Redis/DB/Formatting): {preprocessing_duration_ms:.2f}ms")
            logger.info(
                f"Code execution completed for candidate {candidate_id}, question {request.question_id}. "
                f"Execution service response time: {execution_duration_ms:.2f}ms"
            )
        except httpx.TimeoutException:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service Timeout: {execution_duration_ms:.2f}ms elapsed before timeout (Question: {request.question_id})")
            logger.error(
                f"Execution service timeout for candidate {candidate_id}, question {request.question_id}. "
                f"Time elapsed before timeout: {execution_duration_ms:.2f}ms"
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Code execution timed out. Please try again."
            )
        except httpx.ConnectError:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service Connection Error: {execution_duration_ms:.2f}ms elapsed before error (Question: {request.question_id})")
            logger.error(
                f"Execution service connection error for candidate {candidate_id}, question {request.question_id}. "
                f"Time elapsed before connection error: {execution_duration_ms:.2f}ms"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Code execution service is currently unavailable. Please try again later."
            )
        except httpx.HTTPStatusError as e:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service HTTP Error: {execution_duration_ms:.2f}ms elapsed (Status: {e.response.status_code}, Question: {request.question_id})")
            logger.error(
                f"Execution service HTTP error {e.response.status_code}: {e.response.text}. "
                f"Time elapsed: {execution_duration_ms:.2f}ms"
            )
            try:
                error_detail = e.response.json().get("detail", e.response.text)
            except:
                error_detail = e.response.text
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Execution service error: {error_detail}"
            )
        except Exception as e:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service Unexpected Error: {execution_duration_ms:.2f}ms elapsed (Error: {str(e)[:50]}, Question: {request.question_id})")
            logger.error(
                f"Unexpected error calling execution service: {str(e)}. "
                f"Time elapsed: {execution_duration_ms:.2f}ms"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to execute code: {str(e)}"
            )
        
        # Step 7: Sanitize response based on mode
        postprocessing_start_time = time.perf_counter()
        if request.mode == "run_all" and "test_results" in execution_result:
            # Sanitize hidden test cases (remove input/expected_output)
            # Build a set of sample test case IDs for quick lookup
            sample_test_case_ids = set()
            if sample_test_cases:
                for idx, tc in enumerate(sample_test_cases):
                    if isinstance(tc, dict):
                        sample_id = tc.get("id", f"sample_{idx + 1}")
                        sample_test_case_ids.add(sample_id)
            
            sanitized_results = []
            for result in execution_result.get("test_results", []):
                test_case_id = result.get("test_case_id", "")
                
                # Check if this is a sample test case by ID
                is_sample = test_case_id in sample_test_case_ids or test_case_id.startswith("sample_")
                
                if is_sample:
                    # Keep full details for sample test cases
                    sanitized_results.append(result)
                else:
                    # Sanitize hidden test cases - remove sensitive information
                    sanitized_result = {
                        "test_case_id": test_case_id,
                        "test_case_number": result.get("test_case_number"),
                        "status": result.get("status", "unknown"),
                        "passed": result.get("passed", False),
                        "execution_time_ms": result.get("execution_time_ms"),
                        "cpu_usage_percent": result.get("cpu_usage_percent"),
                        "memory_usage_bytes": result.get("memory_usage_bytes")
                        # Intentionally omitting: input, expected_output, actual_output
                    }
                    sanitized_results.append(sanitized_result)
            
            execution_result["test_results"] = sanitized_results
        
        postprocessing_end_time = time.perf_counter()
        postprocessing_duration_ms = (postprocessing_end_time - postprocessing_start_time) * 1000
        
        # Step 8: Add execution time to metadata
        metadata = execution_result.get("metadata") or {}
        metadata["execution_service_response_time_ms"] = round(execution_duration_ms, 2)
        metadata["preprocessing_time_ms"] = round(preprocessing_duration_ms, 2)
        metadata["postprocessing_time_ms"] = round(postprocessing_duration_ms, 2)
        
        endpoint_end_time = time.perf_counter()
        total_endpoint_time_ms = (endpoint_end_time - endpoint_start_time) * 1000
        
        # Print detailed timing breakdown
        print(f"   📊 Postprocessing Time (Sanitization): {postprocessing_duration_ms:.2f}ms")
        print(f"   ⏱️  Total Backend Processing Time: {total_endpoint_time_ms:.2f}ms")
        print(f"   📈 Breakdown: Preprocessing={preprocessing_duration_ms:.2f}ms | Execution={execution_duration_ms:.2f}ms | Postprocessing={postprocessing_duration_ms:.2f}ms")
        
        # Step 9: Return response
        return RunCodeResponse(
            execution_id=execution_result.get("execution_id"),
            summary=execution_result.get("summary", {}),
            test_results=execution_result.get("test_results", []),
            metadata=metadata,
            timestamp=execution_result.get("timestamp")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error running code for candidate {candidate_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{candidate_id}/coding/submit", response_model=SubmitCodingAnswerResponse)
async def submit_coding_answer(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: SubmitCodingAnswerRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Submit final answer for a coding question.
    
    This endpoint:
    1. Runs all test cases (sample + hidden) via execution service
    2. Calculates score: 5 points per sample test case passed, 10 points per hidden test case passed
    3. Updates InterviewCoding table with score and test_cases_passed
    4. Uses Redis for optimization (caching test cases)
    
    Only the authenticated candidate can submit answers for their own questions.
    
    Args:
        candidate_id: UUID of the candidate
        request: SubmitCodingAnswerRequest with question_id, language, and code
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        SubmitCodingAnswerResponse with submission results and score
        
    Raises:
        HTTPException: 
            - 400: If validation fails or question not found
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to access another candidate's questions
            - 502: If execution service returns invalid response
            - 503: If execution service is unavailable
            - 504: If execution service times out
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only submit answers for your own questions."
        )
    
    try:
        loader_service = TestDataLoaderService(db)
        sample_test_cases = []
        test_cases = []
        
        # Step 1: Get question from database (test_cases are not cached in Redis due to size)
        coding_question_db = db.query(CodingQuestionBank).filter(
            CodingQuestionBank.uuid == request.question_id
        ).first()
        
        if not coding_question_db:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Coding question with ID {request.question_id} not found"
            )
        
        # Extract test cases from database
        sample_test_cases = coding_question_db.sample_test_cases if coding_question_db.sample_test_cases else []
        test_cases = coding_question_db.test_cases if coding_question_db.test_cases else []
        
        # Step 3: Validate test cases exist
        if not sample_test_cases and not test_cases:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No test cases found for this question"
            )
        
        # Step 4: Format all test cases for execution service (run_all mode)
        formatted_test_cases = []
        
        # Add sample test cases
        if sample_test_cases:
            for idx, tc in enumerate(sample_test_cases):
                if isinstance(tc, dict):
                    formatted_tc = {
                        "id": tc.get("id", f"sample_{idx + 1}"),
                        "input": tc.get("input", ""),
                        "expected_output": tc.get("expected_output", "")
                    }
                    formatted_test_cases.append(formatted_tc)
        
        # Add hidden test cases
        if test_cases:
            for idx, tc in enumerate(test_cases):
                if isinstance(tc, dict):
                    formatted_tc = {
                        "id": tc.get("id", f"hidden_{idx + 1}"),
                        "input": tc.get("input", ""),
                        "expected_output": tc.get("expected_output", "")
                    }
                    formatted_test_cases.append(formatted_tc)
        
        # Step 5: Build request for execution service
        execution_request = {
            "language": request.language,
            "code": request.code,
            "test_cases": formatted_test_cases,
            "user_id": candidate_id,
            "question_id": request.question_id
        }
        
        # Step 6: Call external execution service
        execution_url = settings.CODE_EXECUTION_URL
        
        # Measure execution time
        execution_start_time = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    execution_url,
                    json=execution_request,
                    headers={"Content-Type": "application/json"}
                )
                response.raise_for_status()
                execution_result = response.json()
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            
            # Print and log execution time
            print(f"⏱️  Execution Service Response Time (Submit): {execution_duration_ms:.2f}ms (Question: {request.question_id})")
            logger.info(
                f"Code submission execution completed for candidate {candidate_id}, question {request.question_id}. "
                f"Execution service response time: {execution_duration_ms:.2f}ms"
            )
        except httpx.TimeoutException:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service Timeout (Submit): {execution_duration_ms:.2f}ms elapsed before timeout (Question: {request.question_id})")
            logger.error(
                f"Execution service timeout for candidate {candidate_id}, question {request.question_id}. "
                f"Time elapsed before timeout: {execution_duration_ms:.2f}ms"
            )
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Code execution timed out. Please try again."
            )
        except httpx.ConnectError:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service Connection Error (Submit): {execution_duration_ms:.2f}ms elapsed before error (Question: {request.question_id})")
            logger.error(
                f"Execution service connection error for candidate {candidate_id}, question {request.question_id}. "
                f"Time elapsed before connection error: {execution_duration_ms:.2f}ms"
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Code execution service is currently unavailable. Please try again later."
            )
        except httpx.HTTPStatusError as e:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service HTTP Error (Submit): {execution_duration_ms:.2f}ms elapsed (Status: {e.response.status_code}, Question: {request.question_id})")
            logger.error(
                f"Execution service HTTP error {e.response.status_code}: {e.response.text}. "
                f"Time elapsed: {execution_duration_ms:.2f}ms"
            )
            try:
                error_detail = e.response.json().get("detail", e.response.text)
            except:
                error_detail = e.response.text
            raise HTTPException(
                status_code=e.response.status_code,
                detail=f"Execution service error: {error_detail}"
            )
        except Exception as e:
            execution_end_time = time.perf_counter()
            execution_duration_ms = (execution_end_time - execution_start_time) * 1000
            print(f"⏱️  Execution Service Unexpected Error (Submit): {execution_duration_ms:.2f}ms elapsed (Error: {str(e)[:50]}, Question: {request.question_id})")
            logger.error(
                f"Unexpected error calling execution service: {str(e)}. "
                f"Time elapsed: {execution_duration_ms:.2f}ms"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to execute code: {str(e)}"
            )
        
        # Step 7: Calculate score based on test results
        # Build a set of sample test case IDs for quick lookup
        sample_test_case_ids = set()
        if sample_test_cases:
            for idx, tc in enumerate(sample_test_cases):
                if isinstance(tc, dict):
                    sample_id = tc.get("id", f"sample_{idx + 1}")
                    sample_test_case_ids.add(sample_id)
        
        # Calculate scores
        total_score = 0
        test_cases_passed = 0
        sample_test_cases_passed = 0
        hidden_test_cases_passed = 0
        total_test_cases = len(formatted_test_cases)
        
        test_results = execution_result.get("test_results", [])
        for result in test_results:
            test_case_id = result.get("test_case_id", "")
            passed = result.get("passed", False)
            status_value = result.get("status", "").lower()
            
            # Check if test passed
            is_passed = passed or status_value == "passed"
            
            if is_passed:
                test_cases_passed += 1
                
                # Check if this is a sample test case
                is_sample = test_case_id in sample_test_case_ids or test_case_id.startswith("sample_")
                
                if is_sample:
                    # Sample test case: 5 points
                    total_score += 5
                    sample_test_cases_passed += 1
                else:
                    # Hidden test case: 10 points
                    total_score += 10
                    hidden_test_cases_passed += 1
        
        # Step 8: Update InterviewCoding table
        interview_coding = db.query(InterviewCoding).filter(
            InterviewCoding.candidate_id == candidate_id,
            InterviewCoding.question_uuid == request.question_id
        ).first()
        
        if not interview_coding:
            # Create new record if it doesn't exist
            interview_coding = InterviewCoding(
                candidate_id=candidate_id,
                question_uuid=request.question_id,
                score=total_score,
                test_cases_passed=test_cases_passed,
                difficulty=None  # Can be set from CodingQuestionBank if needed
            )
            db.add(interview_coding)
        else:
            # Update existing record
            interview_coding.score = total_score
            interview_coding.test_cases_passed = test_cases_passed
        
        # Commit to database
        db.commit()
        
        # Step 9: Update last_activity
        try:
            candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
            if candidate and candidate.test_session:
                candidate.test_session.last_activity = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.warning(f"Failed to update last_activity: {str(e)}")
        
        logger.info(
            f"Coding answer submitted for candidate {candidate_id}, question {request.question_id}: "
            f"Score={total_score}, TestCasesPassed={test_cases_passed}/{total_test_cases}"
        )
        
        # Step 10: Return response
        return SubmitCodingAnswerResponse(
            success=True,
            message="Coding answer submitted successfully",
            question_id=request.question_id,
            score=total_score,
            test_cases_passed=test_cases_passed,
            total_test_cases=total_test_cases,
            sample_test_cases_passed=sample_test_cases_passed,
            hidden_test_cases_passed=hidden_test_cases_passed,
            execution_id=execution_result.get("execution_id")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error submitting coding answer for candidate {candidate_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{candidate_id}/coding/finalize", response_model=FinalizeCodingSectionResponse)
async def finalize_coding_section(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Finalize coding section and calculate overall analysis.
    
    This endpoint should be called when the candidate completes the entire coding section.
    It will:
    1. Complete section timing
    2. Calculate overall coding analysis (total score, questions submitted, etc.)
    3. Update interview_analysis_table with coding_analysis
    
    Only the authenticated candidate can finalize their own coding section.
    
    Args:
        candidate_id: UUID of the candidate
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        FinalizeCodingSectionResponse with complete coding section analysis
        
    Raises:
        HTTPException: 
            - 403: If user tries to finalize another candidate's section
            - 404: If candidate not found
            - 500: If analysis calculation fails
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only finalize your own coding section."
        )
    
    try:
        # Get candidate
        candidate = db.query(Candidate).filter(
            Candidate.candidate_id == candidate_id
        ).first()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate {candidate_id} not found"
            )
        
        # Complete section timing
        duration_seconds = complete_section_timing(candidate, "coding")
        duration_minutes = round(duration_seconds / 60, 2) if duration_seconds else 0.0
        
        # Mark coding section as completed in sections_completed
        if candidate.test_session:
            sections_completed = candidate.test_session.sections_completed or {}
            sections_completed["coding"] = True
            candidate.test_session.sections_completed = sections_completed
        
        # Calculate and save coding analysis
        interview_service = InterviewService(db)
        interview_service._update_coding_analysis(candidate_id)
        
        # Commit all changes
        db.commit()
        
        # Get the updated coding analysis
        from models.interview_analysis_table import InterviewAnalysisTable
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        coding_analysis = {}
        if interview_analysis and interview_analysis.coding_analysis:
            coding_analysis = interview_analysis.coding_analysis
        else:
            # Default if not found
            coding_analysis = {
                "total_score": 0.0,
                "time_taken": duration_seconds or 0,
                "total_submitted": 0,
                "total_correct": 0,
                "partially_correct": 0
            }
        
        logger.info(
            f"Coding section finalized for candidate {candidate_id}: "
            f"Score={coding_analysis.get('total_score', 0)}, "
            f"Submitted={coding_analysis.get('total_submitted', 0)}, "
            f"Duration={duration_minutes}min ({duration_seconds}s)"
        )
        
        return FinalizeCodingSectionResponse(
            success=True,
            message="Coding section finalized successfully",
            coding_analysis=coding_analysis,
            duration_seconds=duration_seconds,
            duration_minutes=duration_minutes
        )
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error finalizing coding section for candidate {candidate_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to finalize coding section: {str(e)}"
        )


@router.get("/{candidate_id}/interview-summary", response_model=InterviewSummaryResponse)
async def get_interview_summary(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get interview summary with candidate details.
    
    Returns comprehensive interview analysis including:
    - Candidate information (name, email, role, etc.)
    - Overall summary (4-line LLM-generated summary)
    - MCQ analysis
    - Coding analysis
    - System design analysis
    - Integrity/cheat metrics
    
    Only the authenticated candidate can view their own summary.
    
    Args:
        candidate_id: UUID of the candidate
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        InterviewSummaryResponse with candidate details and all analysis data
        
    Raises:
        HTTPException: 
            - 401: If authentication fails
            - 403: If user is not a candidate or tries to access another candidate's summary
            - 404: If candidate or analysis not found
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only view your own interview summary."
        )
    
    try:
        # Get candidate details
        candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Get interview analysis
        from models.interview_analysis_table import InterviewAnalysisTable
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if not interview_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview analysis not found. The test may not be completed yet."
            )
        
        # Get job information for candidate role
        from models.recruiter_admin_candidate import RecruiterAdminCandidate
        from models.job import Job
        assignment = db.query(RecruiterAdminCandidate).filter(
            RecruiterAdminCandidate.candidate_id == candidate_id
        ).first()
        
        job_role = None
        if assignment:
            job = db.query(Job).filter(Job.job_id == assignment.job_id).first()
            if job:
                job_role = job.job_role
        
        # Build candidate details
        candidate_details = {
            "candidate_id": candidate.candidate_id,
            "candidate_reference_number": candidate.candidate_reference_number,
            "name": candidate.name,
            "email": candidate.email_id,
            "role": job_role or "N/A",
            "status": candidate.status,
            "scheduled_date": candidate.scheduled_date.isoformat() if candidate.scheduled_date else None,
            "test_completed_at": candidate.test_session.test_completed_at.isoformat() if candidate.test_session and candidate.test_session.test_completed_at else None
        }
        
        # Get section timings from test_session - extract only duration
        section_timings = None
        if candidate.test_session and candidate.test_session.section_timings:
            timings_data = candidate.test_session.section_timings
            # Extract only duration_seconds for each section
            section_timings = {}
            for section_name in ['mcq', 'coding', 'system_design']:
                if section_name in timings_data:
                    section_data = timings_data[section_name]
                    # If it's already just a number (duration in seconds), use it directly
                    if isinstance(section_data, (int, float)):
                        section_timings[section_name] = int(section_data)
                    # If it's a dict, extract duration_seconds
                    elif isinstance(section_data, dict):
                        if 'duration_seconds' in section_data:
                            section_timings[section_name] = int(section_data['duration_seconds'])
                        # Also check if duration_minutes exists and convert to seconds
                        elif 'duration_minutes' in section_data:
                            section_timings[section_name] = int(section_data['duration_minutes'] * 60)
        
        # Convert JSONB fields to dict (they're already dicts, but ensure they're serializable)
        mcq_analysis = interview_analysis.mcq_analysis if interview_analysis.mcq_analysis else None
        coding_analysis = interview_analysis.coding_analysis if interview_analysis.coding_analysis else None
        system_design_analysis = interview_analysis.system_design_analysis if interview_analysis.system_design_analysis else None
        cheat_metrics = interview_analysis.cheat_metrics if interview_analysis.cheat_metrics else None
        
        return InterviewSummaryResponse(
            success=True,
            message="Interview summary retrieved successfully",
            candidate=candidate_details,
            summary=interview_analysis.overall_summary,
            mcq_analysis=mcq_analysis,
            coding_analysis=coding_analysis,
            system_design_analysis=system_design_analysis,
            cheat_metrics=cheat_metrics,
            section_timings=section_timings if section_timings else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving interview summary for candidate {candidate_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

