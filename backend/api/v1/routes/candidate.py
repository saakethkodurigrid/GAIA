"""
Candidate API routes for interview-related operations.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_candidate
from models.candidate import Candidate
from services.interview_service import InterviewService
from schemas.mcq import MCQQuestionsResponse, SaveMCQAnswerRequest, SaveMCQAnswerResponse
from schemas.candidate import ScheduleTestRequest, ScheduleTestResponse

router = APIRouter(prefix="/candidate", tags=["Candidate"])


@router.get("/{candidate_id}/mcq-questions", response_model=MCQQuestionsResponse)
async def get_mcq_questions(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    db: Session = Depends(get_db)
):
    """
    Get all MCQ questions and options for a candidate.
    
    This endpoint fetches all MCQ questions from the interview_mcq table
    for the specified candidate. Only returns question text and options,
    no other information from the table.
    
    Args:
        candidate_id: UUID of the candidate
        db: Database session
        
    Returns:
        MCQQuestionsResponse with list of questions and their options
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs while retrieving questions
    """
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
    db: Session = Depends(get_db)
):
    """
    Save or update candidate's answers for multiple MCQ questions.
    
    This endpoint saves all candidate's selected answers for MCQ questions
    in the interview_mcq table. The answers will be stored in the candidate_answer field.
    Frontend sends a list of all questions and answers at once.
    
    Args:
        candidate_id: UUID of the candidate
        request: SaveMCQAnswerRequest containing list of question-answer pairs
        db: Database session
        
    Returns:
        SaveMCQAnswerResponse with success status, counts, and failed questions
        
    Raises:
        HTTPException: 
            - 400: If validation fails or error occurs while saving
    """
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
    interview_service = InterviewService(db)
    response = interview_service.save_test_schedule(current_candidate.candidate_id, request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response

