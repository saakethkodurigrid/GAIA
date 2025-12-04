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
    TestStatusResponse,
    TabCloseCompletionRequest
)
from services.question_assignment_service import QuestionAssignmentService
from services.test_session_service import TestSessionService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/candidate", tags=["Candidate"])


@router.get("/{candidate_id}/mcq-questions", response_model=MCQQuestionsResponse)
async def get_mcq_questions(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Get all MCQ questions and options for a candidate.
    
    This endpoint fetches all MCQ questions from the interview_mcq table
    for the specified candidate. Only returns question text and options,
    no other information from the table.
    
    Only the authenticated candidate can view their own questions.
    
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
    
    interview_service = InterviewService(db)
    response = interview_service.save_mcq_answers(candidate_id, request)
    
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
    
    test_session_service = TestSessionService(db)
    response = test_session_service.create_test_session(candidate_id, request.duration_minutes)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.post("/{candidate_id}/test/heartbeat", response_model=HeartbeatResponse)
async def update_heartbeat(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: HeartbeatRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Update heartbeat timestamp for a test session.
    
    This lightweight endpoint updates the last_heartbeat and last_activity
    timestamps to track candidate activity. Returns server timestamp for timer sync.
    
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
    
    test_session_service = TestSessionService(db)
    response = test_session_service.update_heartbeat(candidate_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.post("/{candidate_id}/test/complete", response_model=CompleteTestResponse)
async def complete_test(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: CompleteTestRequest = ...,
    completion_method: str = "manual",
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Complete a test session and save all answers.
    
    This endpoint saves all candidate answers (MCQ, Coding, System Design),
    marks the test session as completed, and updates candidate status.
    The endpoint is idempotent - safe to call multiple times.
    
    Only the authenticated candidate can complete their own test.
    
    Args:
        candidate_id: UUID of the candidate
        request: CompleteTestRequest with all answers
        completion_method: How test was completed ('manual', 'tab_close', 'timer_expired', etc.)
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
    
    # Validate completion_method
    valid_methods = ['manual', 'tab_close', 'timer_expired', 'heartbeat_timeout', 'auto']
    if completion_method not in valid_methods:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid completion_method. Must be one of: {', '.join(valid_methods)}"
        )
    
    test_session_service = TestSessionService(db)
    response = test_session_service.complete_test_session(candidate_id, completion_method, request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.post("/{candidate_id}/test/complete-tab-close", response_model=CompleteTestResponse)
async def complete_test_tab_close(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    request: TabCloseCompletionRequest = ...,
    current_candidate: Candidate = Depends(get_current_candidate),
    db: Session = Depends(get_db)
):
    """
    Complete test session on tab close (optimized for sendBeacon).
    
    This endpoint is specifically designed for tab closure detection.
    It accepts a simplified request format optimized for sendBeacon API.
    Automatically sets completion_method to 'tab_close'.
    
    Only the authenticated candidate can complete their own test.
    
    Args:
        candidate_id: UUID of the candidate
        request: TabCloseCompletionRequest with answers in simplified format
        current_candidate: Authenticated candidate (from dependency)
        db: Database session
        
    Returns:
        CompleteTestResponse with completion confirmation
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs
            - 401: If authentication fails
            - 403: If user is not a candidate
    """
    # Verify candidate_id matches authenticated user
    if current_candidate.candidate_id != candidate_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You can only complete your own test."
        )
    
    # Convert TabCloseCompletionRequest to CompleteTestRequest format
    # Convert simplified MCQ answers format to SaveMCQAnswerRequest
    mcq_request = None
    if request.mcq_answers:
        from schemas.mcq import MCQAnswerItem
        mcq_items = [
            MCQAnswerItem(
                question_uuid=item.get("question_uuid", ""),
                candidate_answer=item.get("candidate_answer", "")
            )
            for item in request.mcq_answers
        ]
        from schemas.mcq import SaveMCQAnswerRequest
        mcq_request = SaveMCQAnswerRequest(answers=mcq_items)
    
    complete_request = CompleteTestRequest(
        mcq_answers=mcq_request,
        coding_answers=request.coding_answers,
        system_design_data=request.system_design_data,
        sections_completed=request.sections_completed
    )
    
    test_session_service = TestSessionService(db)
    response = test_session_service.complete_test_session(candidate_id, "tab_close", complete_request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


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
    
    test_session_service = TestSessionService(db)
    response = test_session_service.get_test_status(candidate_id)
    
    return response

