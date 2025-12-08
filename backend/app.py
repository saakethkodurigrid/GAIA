"""
Main FastAPI application entry point.
"""
# Compatibility patch for sentence-transformers with newer huggingface_hub
# This must be done before any imports that use sentence-transformers
try:
    import huggingface_hub
    # If cached_download doesn't exist, create an alias to hf_hub_download
    if not hasattr(huggingface_hub, 'cached_download'):
        if hasattr(huggingface_hub, 'hf_hub_download'):
            # Create a compatibility wrapper
            def cached_download(*args, **kwargs):
                # hf_hub_download has slightly different signature, adapt if needed
                return huggingface_hub.hf_hub_download(*args, **kwargs)
            huggingface_hub.cached_download = cached_download
except (ImportError, AttributeError):
    pass

# Patch fastapi_mail to ensure SecretStr is available before it's imported
# This fixes the NameError: name 'SecretStr' is not defined issue
# We inject SecretStr into the builtins namespace so it's available globally
try:
    from pydantic import SecretStr
    import builtins
    # Make SecretStr available in the global namespace
    # This ensures fastapi_mail.config can find it when defining ConnectionConfig
    if not hasattr(builtins, 'SecretStr'):
        builtins.SecretStr = SecretStr
except (ImportError, AttributeError):
    # pydantic not installed or patching failed, continue anyway
    pass

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
from core.config import settings
from api.v1.routes import auth_router, admin_router, candidate_router, system_design_router, blob_storage_router

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
app.include_router(blob_storage_router, prefix="/api/v1")

# Background scheduler for test cleanup and Redis sync
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from core.database import get_db
from services.test_cleanup_service import TestCleanupService
from services.redis_sync_service import RedisSyncService
from sqlalchemy.orm import Session

scheduler = AsyncIOScheduler()

async def sync_redis_to_postgresql():
    """Background job to sync Redis data to PostgreSQL periodically."""
    logger = logging.getLogger(__name__)
    try:
        # Get database session
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # Check if there are any active tests first
            from models.candidate import Candidate
            active_count = db.query(Candidate).filter(
                Candidate.status == 'in progress'
            ).count()
            
            # Skip if no active tests
            if active_count == 0:
                logger.info("No active tests found, skipping Redis sync")
                return
            
            logger.info(f"Found {active_count} active test(s), proceeding with Redis sync")
            
            # Get all active tests
            active_candidates = db.query(Candidate).filter(
                Candidate.status == 'in progress'
            ).all()
            
            sync_service = RedisSyncService(db)
            synced_count = 0
            
            # Sync answers for active candidates
            for candidate in active_candidates:
                try:
                    # Sync answers from Redis to PostgreSQL
                    result = sync_service.sync_all_answers_to_postgresql(candidate.candidate_id)
                    if result.get("success"):
                        synced_count += 1
                except Exception as e:
                    logger.error(f"Error syncing candidate {candidate.candidate_id}: {str(e)}")
            
            # Also sync all active system design sessions (may include sessions for candidates not in 'in progress' status)
            try:
                system_design_result = sync_service.sync_all_system_design_sessions()
                if system_design_result.get("success"):
                    logger.info(f"Synced {system_design_result.get('synced_count', 0)} system design sessions")
                else:
                    logger.warning(f"System design sync had {system_design_result.get('failed_count', 0)} failures")
            except Exception as e:
                logger.error(f"Error syncing system design sessions: {str(e)}")
            
            if synced_count > 0:
                logger.info(f"Background sync completed: {synced_count} candidates synced from Redis to PostgreSQL")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in background Redis sync job: {str(e)}")

async def check_and_auto_complete_stale_tests():
    """Background job to check for stale tests and auto-complete them."""
    logger = logging.getLogger(__name__)
    try:
        # Get database session
        db_gen = get_db()
        db: Session = next(db_gen)
        
        try:
            # Check if there are any active tests first
            from models.candidate import Candidate
            active_count = db.query(Candidate).filter(
                Candidate.status == 'in progress'
            ).count()
            
            # Skip if no active tests
            if active_count == 0:
                logger.info("No active tests found, skipping stale test cleanup")
                return
            
            logger.info(f"Found {active_count} active test(s), proceeding with stale test cleanup")
            
            cleanup_service = TestCleanupService(db)
            result = cleanup_service.process_stale_tests()
            
            if result.get("success") and result.get("completed", 0) > 0:
                logger.info(f"Background cleanup: {result['completed']} stale tests auto-completed")
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error in background test cleanup job: {str(e)}")

# Start scheduler when app starts
@app.on_event("startup")
async def startup_event():
    """Start background jobs on application startup."""
    try:
        # Schedule periodic Redis sync (every 5 minutes)
        scheduler.add_job(
            sync_redis_to_postgresql,
            trigger=IntervalTrigger(minutes=settings.BACKGROUND_SYNC_INTERVAL_MINUTES),
            id='redis_sync_job',
            replace_existing=True
        )
        
        # Schedule stale test cleanup (every 5 minutes)
        scheduler.add_job(
            check_and_auto_complete_stale_tests,
            trigger=IntervalTrigger(minutes=settings.BACKGROUND_SYNC_INTERVAL_MINUTES),
            id='stale_test_cleanup_job',
            replace_existing=True
        )
        
        scheduler.start()
        logging.getLogger(__name__).info("Background scheduler started: Redis sync and stale test cleanup jobs scheduled")
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to start background scheduler: {str(e)}")

# Shutdown scheduler when app stops
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown background jobs on application shutdown."""
    try:
        if scheduler.running:
            scheduler.shutdown()
            logging.getLogger(__name__).info("Background scheduler stopped")
    except Exception as e:
        logging.getLogger(__name__).error(f"Error shutting down scheduler: {str(e)}")

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
