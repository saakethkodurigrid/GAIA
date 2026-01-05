"""
Authentication API routes for Google OAuth SSO.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
import logging
import base64
from urllib.parse import urlencode
from core.database import get_db
from services.auth_service import AuthService
from schemas.auth import (
    GoogleTokenRequest,
    CandidateLoginRequest,
    AuthResponse,
    GoogleAuthURLResponse,
    ErrorResponse,
    CandidateStatus
)
from core.security import GoogleOAuth
from core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])
google_oauth = GoogleOAuth()


@router.get("/google/login", response_model=GoogleAuthURLResponse)
async def google_login(state: str = None):
    """
    Initiate Google OAuth login.
    Returns the Google OAuth authorization URL.
    
    Args:
        state: Optional state parameter for CSRF protection
        
    Returns:
        Google OAuth authorization URL
    """
    auth_url = google_oauth.get_google_auth_url(state=state)
    return GoogleAuthURLResponse(auth_url=auth_url, state=state)


@router.get("/google/callback")
async def google_callback(
    code: Optional[str] = Query(None, description="Authorization code from Google OAuth"),
    error: Optional[str] = Query(None, description="Error from Google OAuth"),
    state: Optional[str] = Query(None, description="State parameter for CSRF protection"),
    return_json: Optional[bool] = Query(False, description="Return JSON instead of redirecting (for testing)"),
    db: Session = Depends(get_db)
):
    """
    Google OAuth callback endpoint.
    Exchanges authorization code for token and authenticates user.
    Then redirects to backend callback endpoint with auth result.
    
    Args:
        code: Authorization code from Google OAuth (required if no error)
        error: Error message from Google OAuth (if authentication failed)
        state: State parameter for CSRF protection
        return_json: Return JSON instead of redirecting (for testing)
        db: Database session
        
    Returns:
        RedirectResponse to backend callback page with auth data, or JSON if return_json=True
    """
    # Get frontend URL from settings (for redirecting to frontend callback page)
    # FRONTEND_URL is already validated in config.py to ensure it's set and is a valid absolute URL
    frontend_url = settings.FRONTEND_URL
    callback_url = f"{frontend_url}/auth/callback"
    
    # Debug logging
    logger = logging.getLogger(__name__)
    logger.info(f"OAuth callback received - code: {code is not None}, error: {error}, state: {state}, return_json: {return_json}")
    logger.info(f"Frontend URL: '{frontend_url}', Callback URL: '{callback_url}'")
    
    # Handle OAuth errors from Google
    if error:
        error_params = urlencode({
            'error': error,
            'state': state or ''
        })
        return RedirectResponse(url=f"{callback_url}?{error_params}", status_code=302)
    
    # Check if code is provided
    if not code:
        error_params = urlencode({
            'error': 'Missing authorization code. Please try logging in again.',
            'state': state or ''
        })
        return RedirectResponse(url=f"{callback_url}?{error_params}", status_code=302)
    
    # Exchange code for token
    try:
        id_token_str = google_oauth.get_google_token_from_code(code)
    except ValueError as e:
        error_params = urlencode({
            'error': str(e),
            'state': state or ''
        })
        return RedirectResponse(url=f"{callback_url}?{error_params}", status_code=302)
    except Exception as e:
        error_params = urlencode({
            'error': f"Unexpected error during token exchange: {str(e)}",
            'state': state or ''
        })
        return RedirectResponse(url=f"{callback_url}?{error_params}", status_code=302)
    
    if not id_token_str:
        error_params = urlencode({
            'error': 'Failed to exchange authorization code for token. No ID token received.',
            'state': state or ''
        })
        return RedirectResponse(url=f"{callback_url}?{error_params}", status_code=302)
    
    # Extract candidate_id from state if present (for scheduling links)
    candidate_id = None
    if state:
        try:
            # Try to decode state as base64 JSON (if it contains candidate_id)
            state_decoded = base64.b64decode(state).decode()
            state_data = json.loads(state_decoded)
            if isinstance(state_data, dict) and 'candidate_id' in state_data:
                candidate_id = state_data.get('candidate_id')
                logger.info(f"Extracted candidate_id from state: {candidate_id}")
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError):
            # If state is not JSON, treat it as plain CSRF token (for admin/recruiter)
            logger.info("State is plain CSRF token (no candidate_id)")
            pass
    
    # Authenticate user
    auth_service = AuthService(db)
    response = auth_service.authenticate_user(token=id_token_str, candidate_id=candidate_id)
    
    # Log authentication result
    logger.info(f"Authentication result: success={response.success}, user_type={response.user_type.value if response.user_type else None}, message={response.message}")
    logger.info(f"Response details: email={response.email}, name={response.name}, status={response.status.value if response.status else None}, candidate_id={response.candidate_id}")
    
    # If return_json is True, return JSON response instead of redirecting (for testing)
    if return_json:
        logger.info("Returning JSON response instead of redirecting (return_json=true)")
        return response
    
    if not response.success:
        # Special handling for in progress status (multiple login)
        if response.status == CandidateStatus.IN_PROGRESS:
            error_params = urlencode({
                'error': response.message,
                'error_code': 'IN_PROGRESS',
                'state': state or ''
            })
            return RedirectResponse(url=f"{callback_url}?{error_params}", status_code=302)
        
        error_params = urlencode({
            'error': response.message,
            'state': state or ''
        })
        return RedirectResponse(url=f"{callback_url}?{error_params}", status_code=302)
    
    # Encode auth response as base64 JSON for URL parameter
    auth_data = {
        'success': response.success,
        'message': response.message,
        'user_type': response.user_type.value if response.user_type else None,
        'email': response.email,
        'name': response.name,
        'status': response.status.value if response.status else None,
        'candidate_id': response.candidate_id,
        'job_role': response.job_role,
        'id_token': id_token_str,  # Include Google ID token for API authentication
    }
    
    # Add redirect_url only if it exists in the response
    if hasattr(response, 'redirect_url') and response.redirect_url:
        auth_data['redirect_url'] = response.redirect_url
    
    # Encode auth data
    auth_json = json.dumps(auth_data)
    auth_encoded = base64.urlsafe_b64encode(auth_json.encode()).decode()
    
    # Redirect to backend with auth data
    redirect_params = urlencode({
        'auth': auth_encoded,
        'state': state or ''
    })
    
    redirect_url = f"{callback_url}?{redirect_params}"
    
    # Debug logging
    logger.info(f"Redirecting to frontend: {redirect_url}")
    logger.info(f"Auth data: {auth_data}")
    
    # CRITICAL: Use status_code 302 (Found) for redirect
    # FastAPI RedirectResponse automatically sets Location header
    # Make sure we're returning RedirectResponse, not JSON
    redirect_response = RedirectResponse(url=redirect_url, status_code=302)
    
    # Set headers explicitly to ensure redirect works
    redirect_response.headers["Location"] = redirect_url
    
    logger.info(f"Created RedirectResponse with status {redirect_response.status_code}")
    logger.info(f"RedirectResponse Location header: {redirect_response.headers.get('Location')}")
    
    # IMPORTANT: Return RedirectResponse, not the auth_data dict
    return redirect_response


@router.post("/candidate/login", response_model=AuthResponse)
async def candidate_login(
    request: CandidateLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Candidate login endpoint with UUID.
    
    Flow:
    1. Verify Google token
    2. Check if candidate_id exists in CANDIDATE table
    3. Check if email matches
    4. Route based on status:
       - 'shortlisted' -> scheduled page
       - 'scheduled' -> test landing page
       - 'completed' -> thank you page
       - 'in progress' -> error (multiple login)
    
    Args:
        request: Candidate login request with token and candidate_id
        db: Database session
        
    Returns:
        AuthResponse with redirect URL or error
    """
    auth_service = AuthService(db)
    response = auth_service.authenticate_candidate(
        token=request.token,
        candidate_id=request.candidate_id
    )
    
    if not response.success:
        # Special handling for in progress status (multiple login)
        if response.status == CandidateStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=response.message
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=response.message
        )
    
    return response


@router.post("/login", response_model=AuthResponse)
async def general_login(
    request: GoogleTokenRequest,
    candidate_id: Optional[str] = Query(None, description="Optional candidate UUID for candidate authentication"),
    db: Session = Depends(get_db)
):
    """
    General login endpoint that handles both admin and candidate authentication.
    
    Flow:
    1. Verify Google token
    2. Check domain:
       - If @griddynamics.com:
         - Check RECRUITER_ADMIN table -> Admin dashboard
         - If not found, candidate_id is REQUIRED -> Candidate authentication
       - If not @griddynamics.com:
         - candidate_id is REQUIRED -> Candidate authentication
    3. If user not found anywhere -> Access denied
    
    Note: For candidates, candidate_id is REQUIRED. For admin/recruiter, candidate_id is optional.
    
    Args:
        request: Google OAuth token request
        candidate_id: Optional candidate UUID (REQUIRED for candidates)
        db: Database session
        
    Returns:
        AuthResponse with redirect URL or error
    """
    auth_service = AuthService(db)
    response = auth_service.authenticate_user(token=request.token, candidate_id=candidate_id)
    
    if not response.success:
        # Special handling for in progress status (multiple login)
        if response.status == CandidateStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=response.message
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=response.message
        )
    
    return response