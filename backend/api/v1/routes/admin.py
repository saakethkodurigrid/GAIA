"""
Admin API routes for managing recruiters and admins.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_admin
from models.recruiter_admin import RecruiterAdmin
from services.admin_service import AdminService
from schemas.admin import (
    AddRecruiterAdminRequest,
    AddRecruiterAdminResponse,
    AddJobRequest,
    AddJobResponse,
    ListJobsResponse,
    ListInterviewsResponse,
    AssignedQuestionResponse
)
from services.job_service import JobService
from services.interview_service import InterviewService
from services.question_assignment_service import QuestionAssignmentService
from core.dependencies import get_current_recruiter_admin

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.post("/add-recruiter-admin", response_model=AddRecruiterAdminResponse)
async def add_recruiter_admin(
    request: AddRecruiterAdminRequest,
    current_admin: RecruiterAdmin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Add a new recruiter or admin to the system.
    
    This endpoint allows admins to add new recruiters (role_id = 1) or admins (role_id = 2).
    Only users with admin role (role_id = 2) can access this endpoint.
    
    Args:
        request: AddRecruiterAdminRequest with recruiter or admin details
            - role_id: 1 for Recruiter, 2 for Admin
        current_admin: Current admin user (verified by dependency)
        db: Database session
        
    Returns:
        AddRecruiterAdminResponse with success status and created user data
        
    Raises:
        HTTPException: 
            - 400: If validation fails (invalid role_id, email exists, etc.)
            - 401: If authentication fails
            - 403: If user is not an admin
    """
    admin_service = AdminService(db)
    response = admin_service.add_recruiter_admin(request)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.post("/add-job", response_model=AddJobResponse)
async def add_job(
    request: AddJobRequest,
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Add a new job to the system.
    
    This endpoint allows recruiters and admins to create new jobs.
    Only users with recruiter (role_id = 1) or admin (role_id = 2) role can access this endpoint.
    
    Args:
        request: AddJobRequest with job details
            - job_role: Job role/title
            - job_description: Job description
        current_user: Current recruiter/admin user (verified by dependency)
        db: Database session
        
    Returns:
        AddJobResponse with success status and created job data
        
    Raises:
        HTTPException: 
            - 400: If validation fails or database error occurs
            - 401: If authentication fails
            - 403: If user is not a recruiter or admin
    """
    job_service = JobService(db)
    response = job_service.add_job(request, current_user.email_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get("/list-jobs", response_model=ListJobsResponse)
async def list_jobs(
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    List all jobs in the system.
    
    - Recruiters (role_id = 1): Only see jobs they created
    - Admins (role_id = 2): See all jobs created by everyone
    
    Args:
        current_user: Current recruiter/admin user (verified by dependency)
        db: Database session
        
    Returns:
        ListJobsResponse with list of jobs
        
    Raises:
        HTTPException: 
            - 400: If an error occurs while retrieving jobs
            - 401: If authentication fails
            - 403: If user is not a recruiter or admin
    """
    job_service = JobService(db)
    response = job_service.list_jobs(current_user.email_id, current_user.role_id)
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get("/list-interviews", response_model=ListInterviewsResponse)
async def list_interviews(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD). If provided without end_date, filters for that specific date. If not provided, defaults to today."),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD). Optional. If provided with start_date, filters for date range (inclusive)."),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    List interviews with flexible date filtering.
    
    Handles three scenarios:
    1. Date range: Both start_date and end_date provided
       Example: ?start_date=2025-01-15&end_date=2025-01-20
       Returns: All interviews from Jan 15 to Jan 20 (inclusive)
    
    2. Single date: Only start_date provided
       Example: ?start_date=2025-01-15
       Returns: All interviews on Jan 15
    
    3. Today's schedule: No dates provided (or frontend sends current date)
       Example: ?start_date=2025-01-15 (where 2025-01-15 is today)
       Returns: All interviews scheduled for today
    
    - Recruiters (role_id = 1): Only see interviews for candidates assigned to them
    - Admins (role_id = 2): See all interviews
    
    Args:
        start_date: Optional start date in YYYY-MM-DD format
        end_date: Optional end date in YYYY-MM-DD format
        current_user: Current recruiter/admin user (verified by dependency)
        db: Database session
        
    Returns:
        ListInterviewsResponse with list of interviews
        
    Raises:
        HTTPException: 
            - 400: If date format is invalid, start_date > end_date, or error retrieving interviews
            - 401: If authentication fails
            - 403: If user is not a recruiter or admin
    """
    # Parse dates
    parsed_start_date = None
    parsed_end_date = None
    
    if start_date:
        try:
            parsed_start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Expected YYYY-MM-DD (e.g., 2025-01-15)"
            )
    
    if end_date:
        try:
            parsed_end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Expected YYYY-MM-DD (e.g., 2025-01-15)"
            )
    
    # Validate: if end_date is provided, start_date must also be provided
    if end_date and not start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date cannot be provided without start_date"
        )
    
    interview_service = InterviewService(db)
    response = interview_service.list_interviews(
        current_user.email_id,
        current_user.role_id,
        parsed_start_date,
        parsed_end_date
    )
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get("/list-interviews/today", response_model=ListInterviewsResponse)
async def list_today_interviews(
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    List all interviews scheduled for today.
    
    This is a convenience endpoint - same as GET /interviews with no parameters.
    Kept for backward compatibility.
    
    - Recruiters (role_id = 1): Only see interviews for candidates assigned to them
    - Admins (role_id = 2): See all interviews scheduled for today
    
    Args:
        current_user: Current recruiter/admin user (verified by dependency)
        db: Database session
        
    Returns:
        ListInterviewsResponse with list of interviews scheduled for today
        
    Raises:
        HTTPException: 
            - 400: If an error occurs while retrieving interviews
            - 401: If authentication fails
            - 403: If user is not a recruiter or admin
    """
    interview_service = InterviewService(db)
    response = interview_service.list_interviews(
        current_user.email_id,
        current_user.role_id,
        None,  # No start_date - defaults to today
        None   # No end_date
    )
    
    if not response.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get("/candidates/{candidate_id}/assigned-question", response_model=AssignedQuestionResponse)
async def get_assigned_question(
    candidate_id: str = Path(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Get the assigned system design question for a candidate.
    
    Only recruiters and admins can view assigned questions.
    
    Args:
        candidate_id: Candidate UUID
        current_user: Current recruiter/admin user (verified by dependency)
        db: Database session
        
    Returns:
        AssignedQuestionResponse with question details
        
    Raises:
        HTTPException: 
            - 404: If candidate not found or no question assigned
            - 401: If authentication fails
            - 403: If user is not a recruiter or admin
    """
    assignment_service = QuestionAssignmentService(db)
    question_details = assignment_service.get_assigned_question_details(candidate_id)
    
    if not question_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No question assigned to this candidate or candidate not found"
        )
    
    return AssignedQuestionResponse(**question_details)


