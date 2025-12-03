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
from schemas.admin import AssignedQuestionResponse
from services.question_assignment_service import QuestionAssignmentService

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
    response = await interview_service.save_test_schedule(current_candidate.candidate_id, request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


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

