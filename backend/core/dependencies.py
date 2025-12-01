"""
Dependency functions for FastAPI routes.
"""
import re
from fastapi import Depends, HTTPException, status, Header, Query, Request
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from core.security import GoogleOAuth
from models.recruiter_admin import RecruiterAdmin
from models.candidate import Candidate

google_oauth = GoogleOAuth()


def get_current_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> RecruiterAdmin:
    """
    Dependency to verify that the current user is an admin (role_id = 2).
    
    Args:
        authorization: Authorization header containing "Bearer <token>"
        db: Database session
        
    Returns:
        RecruiterAdmin object if user is an admin
        
    Raises:
        HTTPException: If token is missing, invalid, or user is not an admin
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    # Verify Google token
    user_info = google_oauth.verify_google_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    email = user_info.get('email', '').lower()
    
    # Check if user exists in RECRUITER_ADMIN table
    recruiter_admin = db.query(RecruiterAdmin).filter(
        RecruiterAdmin.email_id == email
    ).first()
    
    if not recruiter_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User is not registered as a recruiter or admin."
        )
    
    # Check if user is an admin (role_id = 2)
    if recruiter_admin.role_id != 2:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only admins can perform this action. Your current role is recruiter."
        )
    
    return recruiter_admin


def get_current_recruiter_admin(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> RecruiterAdmin:
    """
    Dependency to verify that the current user is a recruiter or admin (role_id = 1 or 2).
    
    Args:
        authorization: Authorization header containing "Bearer <token>"
        db: Database session
        
    Returns:
        RecruiterAdmin object if user is a recruiter or admin
        
    Raises:
        HTTPException: If token is missing, invalid, or user is not a recruiter/admin
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    # Verify Google token
    user_info = google_oauth.verify_google_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    email = user_info.get('email', '').lower()
    
    # Check if user exists in RECRUITER_ADMIN table
    recruiter_admin = db.query(RecruiterAdmin).filter(
        RecruiterAdmin.email_id == email
    ).first()
    
    if not recruiter_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. User is not registered as a recruiter or admin."
        )
    
    # Check if user is a recruiter or admin (role_id = 1 or 2)
    if recruiter_admin.role_id not in [1, 2]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only recruiters and admins can perform this action."
        )
    
    return recruiter_admin


def get_current_candidate(
    request: Request,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> Candidate:
    """
    Dependency to verify that the current user is an authenticated candidate.
    
    For schedule/test routes, candidate_id is REQUIRED from invitation link.
    If candidate_id is not provided, access is blocked.
    
    Args:
        request: FastAPI Request object to extract path and query parameters
        authorization: Authorization header containing "Bearer <token>"
        db: Database session
        
    Returns:
        Candidate object if user is authenticated
        
    Raises:
        HTTPException: If token is missing, invalid, candidate_id missing, or user is not a candidate
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid authorization scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer <token>"
        )
    
    # Verify Google token
    user_info = google_oauth.verify_google_token(token)
    if not user_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    email = user_info.get('email', '').lower()
    
    # Try to get candidate_id from path parameters first (for routes like /candidate/{candidate_id}/...)
    # Then fall back to query parameter (for routes like /schedule-test?candidate_id=...)
    path_candidate_id = request.path_params.get('candidate_id')
    query_candidate_id = request.query_params.get('candidate_id')
    final_candidate_id = path_candidate_id or query_candidate_id
    
    # If candidate_id is provided (from path or query), use UUID-based authentication
    if final_candidate_id:
        # Validate UUID format
        uuid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
        if not re.match(uuid_pattern, final_candidate_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid candidate_id format. Must be a valid UUID."
            )
        
        # Check if candidate exists by UUID
        candidate = db.query(Candidate).filter(
            Candidate.candidate_id == final_candidate_id
        ).first()
        
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Candidate not found with the provided ID."
            )
        
        # Verify email matches
        if candidate.email_id.lower() != email:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Email does not match candidate record."
            )
        
        # Verify candidate has correct role_id (0 for candidates)
        if candidate.role_id != 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Invalid role for candidate access."
            )
        
        return candidate
    
    # If candidate_id is NOT provided, try to find candidate by email from token
    # This allows routes like /schedule-test to work with just authentication
    candidate = db.query(Candidate).filter(
        Candidate.email_id == email
    ).first()
    
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. No candidate found with this email address."
        )
    
    # Verify candidate has correct role_id (0 for candidates)
    if candidate.role_id != 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Invalid role for candidate access."
        )
    
    return candidate

