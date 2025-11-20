"""
Admin management schemas for request and response validation.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


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


class JobResponse(BaseModel):
    """Response schema for job information."""
    job_id: str
    job_role: str
    job_description: str
    recruiter_email_id: str


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
    status: str  # Candidate status: registered, scheduled, ongoing, done


class ListInterviewsResponse(BaseModel):
    """Response schema for listing interviews."""
    success: bool
    message: str
    count: int
    interviews: List[InterviewResponse] = []

