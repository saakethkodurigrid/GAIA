"""
Admin API routes for managing recruiters and admins.
"""
import logging
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, File, UploadFile, Form, Request
from typing import List
import json
import json
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
    AddCandidatesBatchResponse,
    CandidateBatchItemResponse,
    CandidateBatchItemRequest,
    CandidateBatchItemRequest,
    FailedFileResponse,
    ResumesListResponse,
    ResumeCandidateResponse,
    ScheduledInterviewsListResponse,
    ScheduledInterviewCandidateResponse,
    CompletedInterviewsListResponse,
    CompletedInterviewCandidateResponse,
    InterviewAnalysisResponse
)
from services.job_service import JobService
from services.interview_service import InterviewService
from services.candidate_batch_service import CandidateBatchService
from core.dependencies import get_current_recruiter_admin

logger = logging.getLogger(__name__)

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


@router.post("/jobs/{job_id}/candidates/batch", response_model=AddCandidatesBatchResponse)
async def add_candidates_batch(
    job_id: str = Path(..., description="Job Reference Number (e.g., JD-783901)", pattern=r'^JD-\d{6}$'),
    request: Request = ...,
    files: List[UploadFile] = File(..., description="Resume files (PDF or DOCX, max 10 files)"),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Add candidates in batch (up to 10) to a job.
    Add candidates in batch (up to 10) to a job.
    
    This endpoint processes candidate data with resume files:
    1. Accepts candidate name, email, and resume file for each candidate
    2. Extracts text from resume files
    This endpoint processes candidate data with resume files:
    1. Accepts candidate name, email, and resume file for each candidate
    2. Extracts text from resume files
    3. Scrubs PII from resume text (for storage and scoring)
    4. Calculates resume score using scrubbed resume (NO PII)
    5. Creates candidate records with provided name/email and scrubbed resume
    5. Creates candidate records with provided name/email and scrubbed resume
    6. Assigns candidates to the specified job
    
    Request Format:
    - Form field: candidates_data (JSON string) containing array: [{"name": "...", "email": "..."}, ...]
    - files: List of resume files matching the order of candidates (files[0] for candidate[0], etc.)
    
    Args:
        job_id: Job reference number (e.g., JD-783901) of the job to assign candidates to
        request: FastAPI Request object to access form data
        files: List of resume files (PDF or DOCX, maximum 10 files) matching candidate order
        current_user: Current recruiter/admin user (verified by dependency)
        db: Database session
        
    Returns:
        AddCandidatesBatchResponse with processing results
        
    Raises:
        HTTPException: 
            - 400: If validation fails, too many candidates, or processing errors
            - 400: If validation fails, too many candidates, or processing errors
            - 401: If authentication fails
            - 403: If user is not a recruiter or admin
            - 404: If job not found
    """
    # Parse form data to extract candidate fields
    form_data = await request.form()
    
    # Extract candidates_data from form (frontend sends as JSON string)
    candidates_data_str = form_data.get('candidates_data')
    
    if not candidates_data_str:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing 'candidates_data' field. Please provide candidate information as JSON."
        )
    
    # Parse JSON string to get candidates list
    try:
        candidates_list = json.loads(candidates_data_str)
    except json.JSONDecodeError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid JSON format in 'candidates_data': {str(e)}"
        )
    
    # Validate candidates_list is a list
    if not isinstance(candidates_list, list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'candidates_data' must be a JSON array of candidate objects."
        )
    
    # Validate candidate count
    if len(candidates_list) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum 10 candidates allowed. Received {len(candidates_list)} candidates."
        )
    
    if len(candidates_list) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one candidate is required in 'candidates_data'."
        )
    
    # Validate files match candidates count
    # if len(files) != len(candidates_list):
    # Validate files match candidates count
    if len(files) != len(candidates_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Number of files ({len(files)}) must match number of candidates ({len(candidates_list)})"
        )
    
    # Validate and parse candidate data
    validated_candidates = []
    for idx, candidate in enumerate(candidates_list):
        try:
            validated_candidate = CandidateBatchItemRequest(**candidate)
            validated_candidates.append(validated_candidate)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid candidate data at index {idx}: {str(e)}"
            )
            detail=f"Number of files ({len(files)}) must match number of candidates ({len(candidates_list)})"
        
    
    # Validate and parse candidate data
    validated_candidates = []
    for idx, candidate in enumerate(candidates_list):
        try:
            validated_candidate = CandidateBatchItemRequest(**candidate)
            validated_candidates.append(validated_candidate)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid candidate data at index {idx}: {str(e)}"
            )
    
    # Validate file types
    allowed_extensions = {'pdf', 'docx', 'doc'}
    invalid_files = []
    for file in files:
        if not file.filename:
            invalid_files.append("Unknown filename")
            continue
        extension = file.filename.lower().split('.')[-1] if '.' in file.filename else ""
        if extension not in allowed_extensions:
            invalid_files.append(file.filename)
    
    if invalid_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid file types. Only PDF and DOCX are allowed. Invalid files: {', '.join(invalid_files)}"
        )
    
    # Get job by reference number (fetches from database)
    job_service = JobService(db)
    try:
        job = job_service.get_job_by_reference_number(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Prepare candidate data with files
    candidate_data_list = []
    for candidate, file in zip(validated_candidates, files):
        candidate_data_list.append({
            "name": candidate.name,
            "email": candidate.email,
            "file": file
        })
    
    # Prepare candidate data with files
    candidate_data_list = []
    for candidate, file in zip(validated_candidates, files):
        candidate_data_list.append({
            "name": candidate.name,
            "email": candidate.email,
            "file": file
        })
    
    # Process batch
    batch_service = CandidateBatchService(db)
    result = await batch_service.process_batch_candidates(
        job_id=job.job_id,  # Use UUID from fetched job object
        candidate_data_list=candidate_data_list,
        recruiter_email=current_user.email_id
    )
    
    # Convert to response schema
    candidate_responses = [
        CandidateBatchItemResponse(**candidate) for candidate in result.get("candidates", [])
    ]
    
    failed_file_responses = [
        FailedFileResponse(**failed) for failed in result.get("failed_files", [])
    ]
    
    response = AddCandidatesBatchResponse(
        success=result.get("success", False),
        message=result.get("message", ""),
        total_files=result.get("total_files", 0),
        successful=result.get("successful", 0),
        failed=result.get("failed", 0),
        candidates=candidate_responses,
        failed_files=failed_file_responses
    )
    
    # If all failed, return 400
    if result.get("successful", 0) == 0 and result.get("failed", 0) > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=response.message
        )
    
    return response


@router.get("/jobs/{job_id}/candidates/resumes", response_model=ResumesListResponse)
async def get_resumes_list(
    job_id: str = Path(..., description="Job Reference Number (e.g., JD-783901)", pattern=r'^JD-\d{6}$'),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of all candidates for resumes view.
    
    Returns all candidates for the specified job regardless of status.
    """
    from models.candidate import Candidate
    from models.recruiter_admin_candidate import RecruiterAdminCandidate
    
    # Get job by reference number (fetches from database)
    job_service = JobService(db)
    try:
        job = job_service.get_job_by_reference_number(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Get all candidates assigned to this job (no status filter)
    candidates = db.query(Candidate).join(
        RecruiterAdminCandidate,
        Candidate.candidate_id == RecruiterAdminCandidate.candidate_id
    ).filter(
        RecruiterAdminCandidate.job_id == job.job_id  # Use UUID from fetched job object
    ).order_by(Candidate.resume_score.desc()).all()
    
    candidate_list = [
        ResumeCandidateResponse(
            candidate_id=c.candidate_reference_number,  # Return reference number only
            name=c.name,
            email_id=c.email_id,
            resume_score=float(c.resume_score) if c.resume_score else 0.0,
            status=c.status
        )
        for c in candidates
    ]
    
    return ResumesListResponse(
        success=True,
        message=f"Found {len(candidate_list)} candidates",
        count=len(candidate_list),
        candidates=candidate_list
    )


@router.get("/jobs/{job_id}/candidates/scheduled-interviews", response_model=ScheduledInterviewsListResponse)
async def get_scheduled_interviews(
    job_id: str = Path(..., description="Job Reference Number (e.g., JD-783901)", pattern=r'^JD-\d{6}$'),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of candidates for scheduled interviews view.
    
    Returns candidates with status: scheduled, in progress, completed, selected, not selected.
    Does not include rejected or shortlisted candidates.
    These are candidates in the interview pipeline.
    """
    from models.candidate import Candidate
    from models.recruiter_admin_candidate import RecruiterAdminCandidate
    
    # Get job by reference number (fetches from database)
    job_service = JobService(db)
    try:
        job = job_service.get_job_by_reference_number(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Get candidates assigned to this job with interview statuses (excluding rejected and shortlisted)
    candidates = db.query(Candidate).join(
        RecruiterAdminCandidate,
        Candidate.candidate_id == RecruiterAdminCandidate.candidate_id
    ).filter(
        RecruiterAdminCandidate.job_id == job.job_id,  # Use UUID from fetched job object
        Candidate.status.in_(['scheduled', 'in progress', 'completed', 'selected', 'not selected'])
    ).order_by(
        Candidate.scheduled_date.asc().nullslast(),
        Candidate.status
    ).all()
    
    candidate_list = [
        ScheduledInterviewCandidateResponse(
            candidate_id=c.candidate_reference_number,  # Return reference number only
            name=c.name,
            email_id=c.email_id,
            interview_status=c.status,
            interview_date=c.scheduled_date.isoformat() if c.scheduled_date else None
        )
        for c in candidates
    ]
    
    return ScheduledInterviewsListResponse(
        success=True,
        message=f"Found {len(candidate_list)} candidates in interview pipeline",
        count=len(candidate_list),
        candidates=candidate_list
    )


@router.get("/jobs/{job_id}/candidates/completed-interviews", response_model=CompletedInterviewsListResponse)
async def get_completed_interviews(
    job_id: str = Path(..., description="Job Reference Number (e.g., JD-783901)", pattern=r'^JD-\d{6}$'),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Get list of candidates for completed interviews view.
    
    Returns candidates with status 'selected' or 'not selected' for the specified job.
    These are candidates who have completed interviews and received final decisions.
    """
    from models.candidate import Candidate
    from models.recruiter_admin_candidate import RecruiterAdminCandidate
    
    # Get job by reference number (fetches from database)
    job_service = JobService(db)
    try:
        job = job_service.get_job_by_reference_number(job_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    
    # Get candidates assigned to this job with final statuses
    candidates = db.query(Candidate).join(
        RecruiterAdminCandidate,
        Candidate.candidate_id == RecruiterAdminCandidate.candidate_id
    ).filter(
        RecruiterAdminCandidate.job_id == job.job_id,  # Use UUID from fetched job object
        Candidate.status.in_(['selected', 'not selected'])
    ).order_by(Candidate.resume_score.desc()).all()
    
    # TODO: Get interview scores from interview_analysis_table if available
    # For now, using resume_score as placeholder
    candidate_list = [
        CompletedInterviewCandidateResponse(
            candidate_id=c.candidate_reference_number,  # Return reference number only
            name=c.name,
            email_id=c.email_id,
            interview_score=float(c.resume_score) if c.resume_score else None,  # Placeholder - should come from interview analysis
            status=c.status,
            report_link=None  # TODO: Generate report link if available
        )
        for c in candidates
    ]
    
    return CompletedInterviewsListResponse(
        success=True,
        message=f"Found {len(candidate_list)} candidates with completed interviews",
        count=len(candidate_list),
        candidates=candidate_list
    )


@router.get("/candidates/{candidate_id}/interview-analysis", response_model=InterviewAnalysisResponse)
async def get_candidate_interview_analysis(
    candidate_id: str = Path(..., description="Candidate Reference Number (e.g., CI-627891)", pattern=r'^CI-\d{6}$'),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Get interview analysis data for a specific candidate.
    
    Returns all analysis fields from interview_analysis_table:
    - MCQ analysis (score, time_taken, attempted, correct by difficulty)
    - Coding analysis (total_score, time_taken, total_submitted, total_correct, partially_correct)
    - System design analysis (score, summary, key_strengths, areas_of_improvement)
    - Cheat metrics (tab_change, full_screen_exits, multiple_face)
    - Overall percentage
    - Result (PASS/FAIL)
    - Overall summary (4-line LLM-generated summary)
    
    Only accessible by recruiters and admins.
    
    Args:
        candidate_id: Candidate reference number (e.g., CI-627891)
        current_user: Authenticated recruiter/admin (from dependency)
        db: Database session
        
    Returns:
        InterviewAnalysisResponse with all analysis data
        
    Raises:
        HTTPException: 
            - 401: If authentication fails
            - 403: If user is not authorized
            - 404: If candidate or analysis not found
    """
    try:
        # Get candidate by reference number
        from services.candidate_service import CandidateService
        candidate_service = CandidateService(db)
        
        try:
            candidate = candidate_service.get_candidate_by_reference_number(candidate_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Get interview analysis using the candidate's UUID
        from models.interview_analysis_table import InterviewAnalysisTable
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate.candidate_id
        ).first()
        
        if not interview_analysis:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview analysis not found for this candidate. The test may not be completed yet."
            )
        
        # Extract all fields from interview_analysis_table
        # JSONB fields are already dicts, ensure they're serializable
        mcq_analysis = interview_analysis.mcq_analysis if interview_analysis.mcq_analysis else None
        coding_analysis = interview_analysis.coding_analysis if interview_analysis.coding_analysis else None
        system_design_analysis = interview_analysis.system_design_analysis if interview_analysis.system_design_analysis else None
        cheat_metrics = interview_analysis.cheat_metrics if interview_analysis.cheat_metrics else None
        
        return InterviewAnalysisResponse(
            success=True,
            message="Interview analysis retrieved successfully",
            candidate_id=candidate.candidate_id,
            mcq_analysis=mcq_analysis,
            coding_analysis=coding_analysis,
            system_design_analysis=system_design_analysis,
            cheat_metrics=cheat_metrics,
            overall_percentage=interview_analysis.overall_percentage,
            result=interview_analysis.result,
            overall_summary=interview_analysis.overall_summary
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving interview analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

