"""
Main FastAPI application entry point.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
from core.config import settings
from api.v1.routes import auth_router, admin_router, candidate_router, system_design_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Initialize FastAPI app
app = FastAPI(
    title="GAIA API",
    description="GAIA Backend API with Google OAuth SSO",
    version="1.0.0"
)

# Configure CORS middleware for frontend integration
# Allow all origins - frontend can be configured separately if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1")
app.include_router(candidate_router, prefix="/api/v1")
app.include_router(system_design_router, prefix="/api/v1")

# Auth callback endpoint (handles redirects from OAuth flow)
@app.get("/auth/callback")
async def auth_callback(
    auth: Optional[str] = None,
    error: Optional[str] = None,
    state: Optional[str] = None
):
    """
    Auth callback endpoint that receives redirects from OAuth flow.
    This endpoint decodes the auth data and returns it as JSON.
    
    Args:
        auth: Base64 encoded auth data from OAuth callback
        error: Error message if authentication failed
        state: State parameter for CSRF protection
        
    Returns:
        JSON response with authentication data
    """
    import base64
    import json
    from fastapi.responses import JSONResponse
    
    if error:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": error,
                "error": error,
                "state": state
            }
        )
    
    if not auth:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Missing authentication data",
                "state": state
            }
        )
    
    try:
        # Decode base64 auth data
        auth_json = base64.urlsafe_b64decode(auth.encode()).decode()
        auth_data = json.loads(auth_json)
        
        return JSONResponse(
            status_code=200,
            content=auth_data
        )
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error decoding auth data: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": f"Failed to decode authentication data: {str(e)}",
                "state": state
            }
        )

# Health check endpoint
@app.get('/')
def index():
    """Root endpoint."""
    return {"message": f"Backend is running on port {settings.PORT}"}

@app.get('/health')
def health():
    """Health check endpoint."""
    return {"status": "healthy", "message": "Backend is running"}

@app.get('/config/check')
def check_config():
    """
    Check configuration values (for debugging).
    This endpoint helps verify that environment variables are set correctly.
    """
    from core.config import settings
    
    # Check if FRONTEND_URL is set
    frontend_url_set = bool(settings.FRONTEND_URL and settings.FRONTEND_URL.strip())
    frontend_url_valid = (
        frontend_url_set and 
        (settings.FRONTEND_URL.startswith('http://') or settings.FRONTEND_URL.startswith('https://'))
    )
    
    return {
        "frontend_url": settings.FRONTEND_URL if frontend_url_set else "NOT SET",
        "frontend_url_set": frontend_url_set,
        "frontend_url_valid": frontend_url_valid,
        "frontend_callback_url": f"{settings.FRONTEND_URL}/auth/callback" if frontend_url_set else "N/A",
        "backend_url": settings.BACKEND_URL,
        "configuration_status": {
            "frontend_url_ok": frontend_url_valid,
            "overall_ok": frontend_url_valid
        }
    }

if __name__ == '__main__':
    print(f"Backend is running on port {settings.PORT}")
    print(f"Access the API at http://localhost:{settings.PORT}")
    print(f"API documentation available at http://localhost:{settings.PORT}/docs")
    
    uvicorn.run(
        "app:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
