"""
Admin API routes for managing recruiters and admins.
"""
import logging
import base64
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, File, UploadFile, Form, Request
from fastapi.responses import StreamingResponse, RedirectResponse
from typing import List
import json
from sqlalchemy.orm import Session
from core.database import get_db
from core.dependencies import get_current_admin
from models.recruiter_admin import RecruiterAdmin
from models.system_config import SystemConfig
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


@router.post("/jobs/{job_id}/candidates/batch-stream")
async def add_candidates_batch_stream(
    job_id: str = Path(..., description="Job Reference Number (e.g., JD-783901)", pattern=r'^JD-\d{6}$'),
    request: Request = ...,
    files: List[UploadFile] = File(..., description="Resume files (PDF or DOCX, max 10 files)"),
    current_user: RecruiterAdmin = Depends(get_current_recruiter_admin),
    db: Session = Depends(get_db)
):
    """
    Add candidates in batch with Server-Sent Events (SSE) streaming.
    
    Streams results as each candidate is processed, providing real-time feedback.
    Each event contains either:
    - A successfully processed candidate with score
    - A failed file with error message
    - A completion message when all candidates are processed
    
    Stream Format:
        data: {"type": "candidate", "data": {...candidate data...}}
        data: {"type": "error", "data": {...error data...}}
        data: {"type": "complete", "data": {...summary...}}
    """
    # Parse form data (same validation as batch endpoint)
    form_data = await request.form()
    candidates_data_str = form_data.get('candidates_data')
    
    if not candidates_data_str:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'Missing candidates_data field'}})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    try:
        candidates_list = json.loads(candidates_data_str)
    except json.JSONDecodeError as e:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Invalid JSON: {str(e)}'}})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    if not isinstance(candidates_list, list):
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': 'candidates_data must be a JSON array'}})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    if len(candidates_list) > 10:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Maximum 10 candidates allowed. Received {len(candidates_list)}'}})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    if len(files) != len(candidates_list):
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Number of files ({len(files)}) must match number of candidates ({len(candidates_list)})'}})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
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
        async def error_stream():
            error_message = f"Invalid file types: {', '.join(invalid_files)}"
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': error_message}})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # Validate and parse candidate data
    validated_candidates = []
    for idx, candidate in enumerate(candidates_list):
        try:
            validated_candidate = CandidateBatchItemRequest(**candidate)
            validated_candidates.append(validated_candidate)
        except Exception as e:
            async def error_stream():
                yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Invalid candidate data at index {idx}: {str(e)}'}})}\n\n"
            return StreamingResponse(
                error_stream(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no"
                }
            )
    
    # Get job by reference number
    job_service = JobService(db)
    try:
        job = job_service.get_job_by_reference_number(job_id)
    except ValueError as e:
        async def error_stream():
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': str(e)}})}\n\n"
        return StreamingResponse(
            error_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    
    # Prepare candidate data with files
    candidate_data_list = []
    for candidate, file in zip(validated_candidates, files):
        candidate_data_list.append({
            "name": candidate.name,
            "email": candidate.email,
            "file": file
        })
    
    # Create a new database session for streaming (to avoid session conflicts)
    from core.database import SessionLocal
    stream_db = SessionLocal()
    
    async def event_stream():
        """Generate SSE stream with candidate processing results"""
        try:
            batch_service = CandidateBatchService(stream_db)
            successful_count = 0
            failed_count = 0
            
            # Process each candidate and stream results
            for idx, candidate_data in enumerate(candidate_data_list):
                try:
                    # Process single candidate
                    result = await batch_service.process_single_candidate(
                        job_id=job.job_id,
                        candidate_data=candidate_data,
                        recruiter_email=current_user.email_id
                    )
                    
                    if result.get("success"):
                        # Stream successful candidate
                        successful_count += 1
                        candidate_response = CandidateBatchItemResponse(**result["candidate"])
                        yield f"data: {json.dumps({'type': 'candidate', 'data': candidate_response.dict()})}\n\n"
                    else:
                        # Stream failed candidate
                        failed_count += 1
                        failed_file = FailedFileResponse(**result["failed_file"])
                        yield f"data: {json.dumps({'type': 'error', 'data': failed_file.dict()})}\n\n"
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"Error processing candidate {idx}: {str(e)}")
                    yield f"data: {json.dumps({'type': 'error', 'data': {'filename': candidate_data['file'].filename or 'unknown', 'error': str(e)}})}\n\n"
            
            # Send completion message
            yield f"data: {json.dumps({'type': 'complete', 'data': {'total': len(candidate_data_list), 'successful': successful_count, 'failed': failed_count}})}\n\n"
            
        except Exception as e:
            logger.error(f"Error in SSE stream: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'data': {'message': f'Stream error: {str(e)}'}})}\n\n"
        finally:
            stream_db.close()
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


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
    
    Returns candidates with status: scheduled, in progress, selected, not selected.
    Does not include rejected, shortlisted, or completed candidates.
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
    
    # Get candidates assigned to this job with interview statuses (excluding rejected, shortlisted, and completed)
    candidates = db.query(Candidate).join(
        RecruiterAdminCandidate,
        Candidate.candidate_id == RecruiterAdminCandidate.candidate_id
    ).filter(
        RecruiterAdminCandidate.job_id == job.job_id,  # Use UUID from fetched job object
        Candidate.status.in_(['scheduled', 'in progress', 'selected', 'not selected'])
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
    
    Returns candidates with status 'completed', 'selected' or 'not selected' for the specified job.
    These are candidates who have completed interviews and may or may not have received final decisions.
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
        Candidate.status.in_(['completed', 'selected', 'not selected'])
    ).order_by(Candidate.resume_score.desc()).all()
    
    # Get interview scores from interview_analysis_table
    from models.interview_analysis_table import InterviewAnalysisTable
    
    candidate_list = []
    for c in candidates:
        # Fetch interview analysis for this candidate
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == c.candidate_id
        ).first()
        
        # Use overall_percentage from interview_analysis_table as interview_score
        interview_score = None
        if interview_analysis and interview_analysis.overall_percentage is not None:
            interview_score = float(interview_analysis.overall_percentage)
        
        candidate_list.append(
            CompletedInterviewCandidateResponse(
                candidate_id=c.candidate_reference_number,  # Return reference number only
                name=c.name,
                email_id=c.email_id,
                resume_score=float(c.resume_score) if c.resume_score else None,
                interview_score=interview_score,
                status=c.status,
                report_link=None  # TODO: Generate report link if available
            )
        )
    
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
    - Candidate image (base64 encoded data URL from blob storage)
    
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
        
        # Fetch the candidate's image from blob storage and encode as base64
        image_data = None
        try:
            from services.blob_storage_service import BlobStorageService
            blob_service = BlobStorageService()
            image_result = blob_service.get_image(candidate.candidate_id)
            if image_result:
                content, content_type, filename = image_result
                # Encode image as base64 data URL
                image_data = f"data:{content_type};base64,{base64.b64encode(content).decode('utf-8')}"
        except Exception as e:
            logger.warning(f"Could not fetch image for candidate {candidate_id}: {str(e)}")
            # Continue without image if it fails
        
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
            overall_summary=interview_analysis.overall_summary,
            image_data=image_data,
            section_timings=section_timings if section_timings else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving interview analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get("/authorize-shared-calendar")
async def authorize_shared_calendar(
    request: Request,
    current_admin: RecruiterAdmin = Depends(get_current_admin),
    db: Session = Depends(get_db),
    return_json: bool = Query(False, description="Return JSON with authorization URL instead of redirecting")
):
    """
    Initiate OAuth flow for shared calendar account authorization.
    Only accessible to admins. Redirects to Google OAuth consent screen.
    
    The admin will sign in with the shared calendar account (e.g., hr@company.com)
    and grant calendar permissions. Tokens are stored in system_config table.
    
    Args:
        return_json: If True, returns JSON with authorization_url instead of redirecting.
                    Useful for API calls from frontend.
    """
    from google_auth_oauthlib.flow import Flow
    from core.config import settings
    from pathlib import Path
    
    # Check if already authorized
    existing = db.query(SystemConfig).filter(
        SystemConfig.config_key == 'calendar_oauth_credentials'
    ).first()
    
    if existing:
        try:
            creds_data = json.loads(existing.config_value)
            response_data = {
                "message": "Calendar already authorized",
                "authorized": True,
                "email": creds_data.get('email', 'Unknown'),
                "authorized_at": existing.updated_at.isoformat() if existing.updated_at else None,
                "authorized_by": existing.updated_by
            }
            # If return_json is requested, return JSON; otherwise redirect is not needed
            if return_json or request.headers.get("accept", "").startswith("application/json"):
                return response_data
            # For direct browser access, could still redirect or return JSON
            return response_data
        except:
            pass
    
    # Get credentials.json path
    credentials_path = Path('credentials.json')
    if not credentials_path.is_absolute():
        backend_dir = Path(__file__).parent.parent.parent.parent
        credentials_path = backend_dir / credentials_path
    
    if not credentials_path.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth credentials file not found. Please ensure credentials.json exists."
        )
    
    # Create OAuth flow with calendar scopes
    calendar_redirect_uri = f"{settings.BACKEND_URL}/api/v1/admin/shared-calendar-callback"
    
    logger.info(f"Creating OAuth flow with redirect_uri: {calendar_redirect_uri}")
    logger.info(f"BACKEND_URL from settings: {settings.BACKEND_URL}")
    
    flow = Flow.from_client_secrets_file(
        str(credentials_path),
        scopes=[
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events'
        ],
        redirect_uri=calendar_redirect_uri
    )
    
    # Explicitly set redirect_uri to ensure it's used
    flow.redirect_uri = calendar_redirect_uri
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='false',
        prompt='consent'  # Force consent to get refresh token
    )
    
    logger.info(f"Admin {current_admin.email_id} initiating calendar authorization")
    logger.info(f"Authorization URL generated with redirect_uri: {calendar_redirect_uri}")
    logger.info(f"IMPORTANT: Make sure this redirect URI is registered in Google Cloud Console!")
    
    # If return_json is True or Accept header requests JSON, return JSON
    if return_json or request.headers.get("accept", "").startswith("application/json"):
        return {
            "authorization_url": authorization_url,
            "message": "Please redirect to the authorization_url to complete OAuth flow"
        }
    
    # Otherwise, redirect directly (for direct browser access)
    return RedirectResponse(url=authorization_url)


@router.get("/shared-calendar-callback")
async def shared_calendar_callback(
    code: str = Query(..., description="Authorization code from Google OAuth"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    db: Session = Depends(get_db)
):
    """
    Handle OAuth callback and store calendar credentials in system_config table.
    This endpoint is called by Google after user grants calendar permission.
    """
    from google_auth_oauthlib.flow import Flow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from core.config import settings
    from pathlib import Path
    
    try:
        # Get credentials.json path
        credentials_path = Path('credentials.json')
        if not credentials_path.is_absolute():
            backend_dir = Path(__file__).parent.parent.parent.parent
            credentials_path = backend_dir / credentials_path
        
        if not credentials_path.exists():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="OAuth credentials file not found"
            )
        
        # Create flow with explicit redirect URI
        calendar_redirect_uri = f"{settings.BACKEND_URL}/api/v1/admin/shared-calendar-callback"
        
        logger.info(f"Processing calendar callback with redirect_uri: {calendar_redirect_uri}")
        
        flow = Flow.from_client_secrets_file(
            str(credentials_path),
            scopes=[
                'https://www.googleapis.com/auth/calendar',
                'https://www.googleapis.com/auth/calendar.events'
            ],
            redirect_uri=calendar_redirect_uri
        )
        
        # Explicitly set redirect_uri to ensure it matches
        flow.redirect_uri = calendar_redirect_uri
        
        # Exchange code for tokens
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        # Get user email from OAuth2 API
        try:
            oauth_service = build('oauth2', 'v2', credentials=credentials)
            user_info = oauth_service.userinfo().get().execute()
            user_email = user_info.get('email', 'Unknown')
        except Exception as e:
            logger.warning(f"Could not fetch user email from OAuth2 API: {e}")
            user_email = 'Unknown'
        
        # Store credentials in database
        creds_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes,
            'email': user_email
        }
        
        # Save or update in system_config
        config = db.query(SystemConfig).filter(
            SystemConfig.config_key == 'calendar_oauth_credentials'
        ).first()
        
        if config:
            config.config_value = json.dumps(creds_data)
            config.updated_by = user_email  # Store who authorized it
        else:
            config = SystemConfig(
                config_key='calendar_oauth_credentials',
                config_value=json.dumps(creds_data),
                updated_by=user_email
            )
            db.add(config)
        
        db.commit()
        
        logger.info(f"Calendar account authorized successfully as {user_email}")
        
        # Redirect to frontend admin dashboard with success message
        from urllib.parse import urlencode
        
        success_params = urlencode({
            "calendar_auth": "success",
            "message": f"Calendar authorized as {user_email}",
            "email": user_email
        })
        
        redirect_url = f"{settings.FRONTEND_URL}/admin?{success_params}"
        logger.info(f"Redirecting to: {redirect_url}")
        
        return RedirectResponse(url=redirect_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Failed to authorize calendar: {e}", exc_info=True)
        db.rollback()
        
        # Redirect to frontend with error message
        from urllib.parse import urlencode
        
        error_params = urlencode({
            "calendar_auth": "error",
            "message": f"Failed to authorize calendar: {str(e)}"
        })
        
        redirect_url = f"{settings.FRONTEND_URL}/admin?{error_params}"
        return RedirectResponse(url=redirect_url, status_code=302)


@router.get("/shared-calendar-status")
async def shared_calendar_status(
    current_admin: RecruiterAdmin = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Check if shared calendar account is authorized.
    Returns authorization status and account email.
    """
    config = db.query(SystemConfig).filter(
        SystemConfig.config_key == 'calendar_oauth_credentials'
    ).first()
    
    if not config:
        return {
            "authorized": False,
            "message": "Calendar account not authorized",
            "email": None
        }
    
    try:
        creds_data = json.loads(config.config_value)
        return {
            "authorized": True,
            "email": creds_data.get('email', 'Unknown'),
            "authorized_at": config.updated_at.isoformat() if config.updated_at else None,
            "authorized_by": config.updated_by
        }
    except Exception as e:
        logger.error(f"Error parsing calendar credentials: {e}")
        return {
            "authorized": False,
            "message": "Invalid calendar credentials",
            "email": None
        }

