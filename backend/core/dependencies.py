"""
Dependency functions for FastAPI routes.
"""
from fastapi import Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional
from core.database import get_db
from core.security import GoogleOAuth
from models.recruiter_admin import RecruiterAdmin

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

