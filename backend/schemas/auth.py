"""
Authentication schemas for request and response validation.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional
from enum import Enum


class UserType(str, Enum):
    """User type enumeration."""
    ADMIN = "admin"
    RECRUITER = "recruiter"
    CANDIDATE = "candidate"


class CandidateStatus(str, Enum):
    """Candidate status enumeration."""
    SHORTLISTED = "shortlisted"
    REJECTED = "rejected"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in progress"
    COMPLETED = "completed"
    SELECTED = "selected"
    NOT_SELECTED = "not selected"


class GoogleTokenRequest(BaseModel):
    """Request schema for Google OAuth token."""
    token: str = Field(..., description="Google OAuth ID token")


class CandidateLoginRequest(BaseModel):
    """Request schema for candidate login with UUID."""
    token: str = Field(..., description="Google OAuth ID token")
    candidate_id: str = Field(..., description="Candidate UUID", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


class AuthResponse(BaseModel):
    """Response schema for authentication."""
    model_config = ConfigDict(extra='ignore')
    
    success: bool
    message: str
    user_type: Optional[UserType] = None
    email: Optional[str] = None
    name: Optional[str] = None
    status: Optional[CandidateStatus] = None
    candidate_id: Optional[str] = None


class GoogleAuthURLResponse(BaseModel):
    """Response schema for Google OAuth URL."""
    auth_url: str
    state: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response schema."""
    success: bool = False
    message: str
    error_code: Optional[str] = None

