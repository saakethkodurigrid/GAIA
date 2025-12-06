"""
Test Cleanup Service for detecting and auto-completing stale tests.
Background job that checks for tests with no heartbeat and auto-completes them.
"""
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from models.candidate import Candidate
from models.test_session import TestSession
from core.redis_client import get_redis_client
from core.config import settings
from services.redis_sync_service import RedisSyncService

logger = logging.getLogger(__name__)


class TestCleanupService:
    """Service for cleaning up stale tests."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.redis_client = get_redis_client()
        self.sync_service = RedisSyncService(db)
    
    def check_stale_tests(self) -> List[Dict[str, Any]]:
        """
        Check for tests with no heartbeat for threshold minutes.
        
        Returns:
            List of stale candidate IDs and their details
        """
        try:
            threshold = datetime.utcnow() - timedelta(minutes=settings.STALE_TEST_THRESHOLD_MINUTES)
            
            # Find candidates with status 'in progress' and no heartbeat for threshold time
            # Join with test_session to check heartbeat
            from sqlalchemy import and_
            stale_candidates = self.db.query(Candidate).join(
                TestSession, Candidate.candidate_id == TestSession.candidate_id, isouter=True
            ).filter(
                and_(
                    Candidate.status == 'in progress',
                    TestSession.last_heartbeat < threshold
                )
            ).all()
            
            stale_list = []
            for candidate in stale_candidates:
                if not candidate.test_session:
                    continue
                    
                # Also check Redis heartbeat (for redundancy)
                redis_heartbeat_key = f"candidate:{candidate.candidate_id}:heartbeat"
                redis_heartbeat = self.redis_client.get(redis_heartbeat_key)
                
                # If Redis heartbeat is also stale or missing, mark as stale
                is_stale = True
                if redis_heartbeat:
                    try:
                        heartbeat_time = datetime.fromisoformat(redis_heartbeat)
                        if heartbeat_time >= threshold:
                            is_stale = False
                    except Exception:
                        pass
                
                if is_stale:
                    stale_list.append({
                        "candidate_id": candidate.candidate_id,
                        "test_start_time": candidate.test_session.test_start_time,
                        "last_heartbeat": candidate.test_session.last_heartbeat,
                        "last_activity": candidate.test_session.last_activity
                    })
            
            logger.info(f"Found {len(stale_list)} stale tests")
            return stale_list
            
        except Exception as e:
            logger.error(f"Error checking stale tests: {str(e)}")
            return []
    
    def auto_complete_stale_test(self, candidate_id: str) -> Dict[str, Any]:
        """
        Auto-complete a stale test by syncing from Redis and marking as completed.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Dictionary with completion results
        """
        try:
            candidate = self.db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
            
            if not candidate:
                return {
                    "success": False,
                    "error": "Candidate not found"
                }
            
            if candidate.status != 'in progress':
                return {
                    "success": False,
                    "error": f"Test is not in progress (status: {candidate.status})"
                }
            
            # Get all answers from Redis
            answers = self.sync_service.get_answers_from_redis(candidate_id)
            progress = self.sync_service.get_progress_from_redis(candidate_id)
            
            # Sync all data from Redis to PostgreSQL
            sync_result = self.sync_service.sync_all_answers_to_postgresql(candidate_id)
            
            if not sync_result.get("success"):
                logger.warning(f"Some data failed to sync for candidate {candidate_id}, but completing test anyway")
            
            # Mark test as completed
            now = datetime.utcnow()
            candidate.status = 'completed'
            
            # Get or create test session
            test_session = candidate.test_session
            if not test_session:
                test_session = TestSession(candidate_id=candidate_id)
                self.db.add(test_session)
                self.db.flush()
            
            test_session.completion_method = 'heartbeat_timeout'
            test_session.test_completed_at = now
            
            # Update sections_completed and section_timings from Redis if available
            if progress:
                if progress.get("sections_completed"):
                    test_session.sections_completed = progress["sections_completed"]
                if progress.get("section_timings"):
                    test_session.section_timings = progress["section_timings"]
            
            self.db.commit()
            
            # Clear Redis keys
            from services.test_data_loader_service import TestDataLoaderService
            loader_service = TestDataLoaderService(self.db)
            loader_service.clear_test_data_from_redis(candidate_id)
            
            logger.info(f"Auto-completed stale test for candidate {candidate_id}")
            
            return {
                "success": True,
                "candidate_id": candidate_id,
                "completed_at": now.isoformat(),
                "sync_result": sync_result
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error auto-completing stale test for candidate {candidate_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def process_stale_tests(self) -> Dict[str, Any]:
        """
        Process all stale tests - check and auto-complete them.
        
        Returns:
            Dictionary with processing results
        """
        try:
            stale_tests = self.check_stale_tests()
            
            completed_count = 0
            failed_count = 0
            results = []
            
            for stale_test in stale_tests:
                candidate_id = stale_test["candidate_id"]
                result = self.auto_complete_stale_test(candidate_id)
                
                if result.get("success"):
                    completed_count += 1
                else:
                    failed_count += 1
                
                results.append({
                    "candidate_id": candidate_id,
                    "result": result
                })
            
            logger.info(f"Processed stale tests: {completed_count} completed, {failed_count} failed")
            
            return {
                "success": True,
                "total_stale": len(stale_tests),
                "completed": completed_count,
                "failed": failed_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error processing stale tests: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

