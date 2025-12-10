"""
Scheduler Manager
Manages background scheduler jobs for test sync and cleanup.
Provides functions to start/stop jobs based on test activity.
"""
import logging
from sqlalchemy.orm import Session
from core.database import get_db
from models.candidate import Candidate

logger = logging.getLogger(__name__)

# Global scheduler reference - will be set by app.py
_scheduler = None


def set_scheduler(scheduler_instance):
    """Set the global scheduler instance."""
    global _scheduler
    _scheduler = scheduler_instance


def has_active_tests(db: Session) -> bool:
    """Check if there are any active tests in the database."""
    try:
        active_count = db.query(Candidate).filter(
            Candidate.status == 'in progress'
        ).count()
        return active_count > 0
    except Exception:
        return False


def start_scheduler_jobs():
    """Start/resume scheduler jobs when tests become active."""
    global _scheduler
    if _scheduler is None:
        logger.warning("Scheduler not initialized, cannot start jobs")
        return
    
    try:
        redis_job = _scheduler.get_job('redis_sync_job')
        cleanup_job = _scheduler.get_job('stale_test_cleanup_job')
        
        if redis_job and redis_job.next_run_time is None:
            _scheduler.resume_job('redis_sync_job')
            logger.info("Resumed Redis sync job - test started")
        if cleanup_job and cleanup_job.next_run_time is None:
            _scheduler.resume_job('stale_test_cleanup_job')
            logger.info("Resumed stale test cleanup job - test started")
    except Exception as e:
        logger.error(f"Error starting scheduler jobs: {str(e)}")


def stop_scheduler_jobs_if_no_active_tests():
    """Pause scheduler jobs if no active tests remain."""
    global _scheduler
    if _scheduler is None:
        logger.warning("Scheduler not initialized, cannot stop jobs")
        return
    
    try:
        db_gen = get_db()
        db: Session = next(db_gen)
        try:
            has_active = has_active_tests(db)
            if not has_active:
                redis_job = _scheduler.get_job('redis_sync_job')
                cleanup_job = _scheduler.get_job('stale_test_cleanup_job')
                
                if redis_job and redis_job.next_run_time is not None:
                    _scheduler.pause_job('redis_sync_job')
                    logger.info("Paused Redis sync job - no active tests")
                if cleanup_job and cleanup_job.next_run_time is not None:
                    _scheduler.pause_job('stale_test_cleanup_job')
                    logger.info("Paused stale test cleanup job - no active tests")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error stopping scheduler jobs: {str(e)}")

