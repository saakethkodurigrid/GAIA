"""
Authentication API routes for Google OAuth SSO.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import Optional
import json
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
    # Get backend URL from settings
    backend_url = settings.BACKEND_URL
    
    # Remove trailing slash if present
    if backend_url and backend_url.endswith('/'):
        backend_url = backend_url.rstrip('/')
    
    # Validate BACKEND_URL is set
    if not backend_url or backend_url.strip() == '':
        import logging
        logger = logging.getLogger(__name__)
        logger.error("BACKEND_URL is not set! Cannot redirect to backend.")
        # Return error as JSON since we can't redirect
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Configuration error: BACKEND_URL is not set. Please configure BACKEND_URL environment variable."
        )
    
    callback_url = f"{backend_url}/auth/callback"
    
    # Debug logging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"OAuth callback received - code: {code is not None}, error: {error}, state: {state}, return_json: {return_json}")
    logger.info(f"BACKEND_URL from settings: '{settings.BACKEND_URL}'")
    logger.info(f"Backend URL (processed): '{backend_url}', Callback URL: '{callback_url}'")
    
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
    
    # Authenticate user
    auth_service = AuthService(db)
    response = auth_service.authenticate_user(token=id_token_str)
    
    # Log authentication result
    logger.info(f"Authentication result: success={response.success}, user_type={response.user_type.value if response.user_type else None}, message={response.message}")
    logger.info(f"Response details: email={response.email}, name={response.name}, status={response.status.value if response.status else None}, candidate_id={response.candidate_id}")
    
    # If return_json is True, return JSON response instead of redirecting (for testing)
    if return_json:
        logger.info("Returning JSON response instead of redirecting (return_json=true)")
        return response
    
    if not response.success:
        # Special handling for ongoing status (multiple login)
        if response.status == CandidateStatus.ONGOING:
            error_params = urlencode({
                'error': response.message,
                'error_code': 'ONGOING',
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
    logger.info(f"Redirecting to backend: {redirect_url}")
    logger.info(f"BACKEND_URL from settings: {settings.BACKEND_URL}")
    logger.info(f"Auth data: {auth_data}")
    
    # Ensure redirect URL is valid
    if not redirect_url.startswith('http://') and not redirect_url.startswith('https://'):
        logger.error(f"Invalid redirect URL (not absolute): {redirect_url}")
        logger.error(f"BACKEND_URL value: {settings.BACKEND_URL}")
        # If BACKEND_URL is not set correctly, we can't redirect, so return error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Configuration error: Invalid redirect URL. BACKEND_URL may not be set correctly.",
                "backend_url": settings.BACKEND_URL,
                "redirect_url": redirect_url,
                "auth_data": auth_data  # Include auth data in error for debugging
            }
        )
    
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
       - 'registered' -> scheduled page
       - 'scheduled' -> test landing page
       - 'done' -> thank you page
       - 'ongoing' -> error (multiple login)
    
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
        # Special handling for ongoing status (multiple login)
        if response.status == CandidateStatus.ONGOING:
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
    db: Session = Depends(get_db)
):
    """
    General login endpoint that handles both admin and candidate authentication.
    
    Flow:
    1. Verify Google token
    2. Check domain:
       - If @griddynamics.com:
         - Check RECRUITER_ADMIN table -> Admin dashboard
         - If not found, check CANDIDATE table -> Status-based routing
       - If not @griddynamics.com:
         - Check CANDIDATE table -> Status-based routing
    3. If user not found anywhere -> Access denied
    
    Args:
        request: Google OAuth token request
        db: Database session
        
    Returns:
        AuthResponse with redirect URL or error
    """
    auth_service = AuthService(db)
    response = auth_service.authenticate_user(token=request.token)
    
    if not response.success:
        # Special handling for ongoing status (multiple login)
        if response.status == CandidateStatus.ONGOING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=response.message
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=response.message
        )
    
    return response

