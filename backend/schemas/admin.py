"""
Admin management schemas for request and response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any


class AddRecruiterAdminRequest(BaseModel):
    """Request schema for adding a recruiter or admin."""
    email_id: EmailStr = Field(..., description="Email address of the recruiter/admin")
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the recruiter/admin")
    role_id: int = Field(..., ge=1, le=2, description="Role ID: 1=Recruiter, 2=Admin")
    phone_number: Optional[str] = Field(None, max_length=20, description="Phone number (optional)")
    location: Optional[str] = Field(None, max_length=255, description="Location (optional)")


class RecruiterAdminResponse(BaseModel):
    """Response schema for recruiter/admin information."""
    email_id: str
    name: str
    role_id: int
    phone_number: Optional[str] = None
    location: Optional[str] = None
    role_name: Optional[str] = None  # Will be populated from role table


class AddRecruiterAdminResponse(BaseModel):
    """Response schema for adding recruiter/admin."""
    success: bool
    message: str
    data: Optional[RecruiterAdminResponse] = None


class AddJobRequest(BaseModel):
    """Request schema for adding a job."""
    job_role: str = Field(..., min_length=1, description="Job role/title")
    job_description: str = Field(..., min_length=1, description="Job description")
    grade: str = Field(..., min_length=1, description="Grade level (e.g., T1, T2, T3, etc.)")


class JobResponse(BaseModel):
    """Response schema for job information."""
    job_id: str
    job_role: str
    job_description: str
    recruiter_email_id: str
    recruiter_name: str
    grade: str


class AddJobResponse(BaseModel):
    """Response schema for adding job."""
    success: bool
    message: str
    data: Optional[JobResponse] = None


class ListJobsResponse(BaseModel):
    """Response schema for listing jobs."""
    success: bool
    message: str
    count: int
    jobs: List[JobResponse] = []


class InterviewResponse(BaseModel):
    """Response schema for interview information."""
    candidate_id: str
    candidate_name: str
    candidate_email: str
    job_id: str
    job_role: str
    recruiter_email: str
    scheduled_date: str  # ISO format datetime string
    status: str  # Candidate status: shortlisted, rejected, scheduled, in progress, completed, selected, not selected


class ListInterviewsResponse(BaseModel):
    """Response schema for listing interviews."""
    success: bool
    message: str
    count: int
    interviews: List[InterviewResponse] = []


class AssignQuestionRequest(BaseModel):
    """Request schema for assigning system design question."""
    question_uuid: Optional[str] = Field(None, description="Question UUID. If not provided, auto-selects based on job role.")


class AssignedQuestionResponse(BaseModel):
    """Response schema for assigned question details."""
    candidate_id: str
    question_uuid: str
    question: str


class AssignQuestionResponse(BaseModel):
    """Response schema for question assignment."""
    success: bool
    message: str
    question_uuid: Optional[str] = None


class CandidateBatchItemRequest(BaseModel):
    """Request schema for individual candidate in batch."""
    name: str = Field(..., min_length=1, max_length=255, description="Candidate name")
    email: EmailStr = Field(..., description="Candidate email address")


class CandidateBatchItemResponse(BaseModel):
    """Response schema for individual candidate in batch."""
    candidate_id: str
    name: str
    email_id: str
    status: str
    resume_score: float
    processing_status: str
    errors: Optional[str] = None


class FailedFileResponse(BaseModel):
    """Response schema for failed file processing."""
    filename: str
    error: str


class AddCandidatesBatchResponse(BaseModel):
    """Response schema for batch candidate addition."""
    success: bool
    message: str
    total_files: int
    successful: int
    failed: int
    candidates: List[CandidateBatchItemResponse] = []
    failed_files: List[FailedFileResponse] = []


class ResumeCandidateResponse(BaseModel):
    """Response schema for candidate in resumes view."""
    candidate_id: str
    name: str
    email_id: str
    resume_score: float
    status: str  # 'shortlisted' or 'rejected'


class ResumesListResponse(BaseModel):
    """Response schema for resumes list."""
    success: bool
    message: str
    count: int
    candidates: List[ResumeCandidateResponse] = []


class ScheduledInterviewCandidateResponse(BaseModel):
    """Response schema for candidate in scheduled interviews view."""
    candidate_id: str
    name: str
    email_id: str
    interview_status: str  # 'scheduled', 'in progress', or 'completed'
    interview_date: Optional[str] = None  # ISO format datetime string


class ScheduledInterviewsListResponse(BaseModel):
    """Response schema for scheduled interviews list."""
    success: bool
    message: str
    count: int
    candidates: List[ScheduledInterviewCandidateResponse] = []


class CompletedInterviewCandidateResponse(BaseModel):
    """Response schema for candidate in completed interviews view."""
    candidate_id: str
    name: str
    email_id: str
    interview_score: Optional[float] = None
    status: str  # 'selected' or 'not selected'
    report_link: Optional[str] = None


class CompletedInterviewsListResponse(BaseModel):
    """Response schema for completed interviews list."""
    success: bool
    message: str
    count: int
    candidates: List[CompletedInterviewCandidateResponse] = []


class InterviewAnalysisResponse(BaseModel):
    """Response schema for interview analysis data."""
    success: bool
    message: str
    candidate_id: str
    mcq_analysis: Optional[Dict[str, Any]] = None
    coding_analysis: Optional[Dict[str, Any]] = None
    system_design_analysis: Optional[Dict[str, Any]] = None
    cheat_metrics: Optional[Dict[str, Any]] = None
    overall_percentage: Optional[int] = None
    result: Optional[str] = None  # 'PASS' or 'FAIL'
    overall_summary: Optional[str] = None
    image_data: Optional[str] = None  # Base64 encoded image data URL

