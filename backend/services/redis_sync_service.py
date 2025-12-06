"""
Redis Sync Service for syncing data from Redis to PostgreSQL.
Handles soft save (Redis) to hard save (PostgreSQL) synchronization.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy.orm import Session
from models.interview_mcq import InterviewMCQ
from models.interview_coding import InterviewCoding
from models.interview_system_design import InterviewSystemDesign
from models.candidate import Candidate
from models.test_session import TestSession
from core.redis_client import get_redis_client
from services.interview_service import InterviewService

logger = logging.getLogger(__name__)


class RedisSyncService:
    """Service for syncing data from Redis to PostgreSQL."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.redis_client = get_redis_client()
    
    def get_answers_from_redis(self, candidate_id: str) -> Dict[str, Any]:
        """
        Get all answers from Redis.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Dictionary with answers for all sections
        """
        try:
            redis_key = f"candidate:{candidate_id}:answers"
            data = self.redis_client.get(redis_key)
            
            if data:
                return json.loads(data)
            return {}
            
        except Exception as e:
            logger.error(f"Error getting answers from Redis for candidate {candidate_id}: {str(e)}")
            return {}
    
    def get_progress_from_redis(self, candidate_id: str) -> Dict[str, Any]:
        """
        Get progress data from Redis.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Dictionary with progress data
        """
        try:
            redis_key = f"candidate:{candidate_id}:progress"
            data = self.redis_client.get(redis_key)
            
            if data:
                return json.loads(data)
            return {}
            
        except Exception as e:
            logger.error(f"Error getting progress from Redis for candidate {candidate_id}: {str(e)}")
            return {}
    
    def sync_mcq_answers_to_postgresql(self, candidate_id: str, mcq_answers: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Sync MCQ answers from Redis to PostgreSQL.
        
        Args:
            candidate_id: UUID of the candidate
            mcq_answers: List of MCQ answers from Redis
            
        Returns:
            Dictionary with sync results
        """
        saved_count = 0
        failed_count = 0
        failed_questions = []
        total_score = 0
        correct_answers = 0
        incorrect_answers = 0
        
        DIFFICULTY_SCORES = {
            "hard": 3,
            "medium": 2,
            "easy": 1
        }
        
        try:
            for answer_data in mcq_answers:
                try:
                    question_uuid = answer_data.get("question_uuid")
                    candidate_answer = answer_data.get("candidate_answer")
                    
                    if not question_uuid:
                        failed_count += 1
                        continue
                    
                    # Find the MCQ record
                    mcq = self.db.query(InterviewMCQ).filter(
                        InterviewMCQ.uuid == question_uuid,
                        InterviewMCQ.candidate_id == candidate_id
                    ).first()
                    
                    if not mcq:
                        failed_count += 1
                        failed_questions.append(question_uuid)
                        continue
                    
                    # Convert candidate_answer to int
                    try:
                        candidate_option_number = int(str(candidate_answer).strip())
                    except (ValueError, AttributeError):
                        failed_count += 1
                        failed_questions.append(question_uuid)
                        continue
                    
                    # Update answer and score
                    mcq.candidate_answer = candidate_option_number
                    
                    difficulty = (mcq.difficulty or "medium").lower()
                    difficulty_score = DIFFICULTY_SCORES.get(difficulty, 1)
                    
                    if candidate_option_number == mcq.correct_answer:
                        mcq.score = difficulty_score
                        total_score += difficulty_score
                        correct_answers += 1
                    else:
                        mcq.score = 0
                        incorrect_answers += 1
                    
                    saved_count += 1
                    
                except Exception as e:
                    logger.error(f"Error syncing MCQ answer for question {answer_data.get('question_uuid')}: {str(e)}")
                    failed_count += 1
                    failed_questions.append(answer_data.get("question_uuid", "unknown"))
                    continue
            
            # Commit all changes
            if saved_count > 0:
                self.db.commit()
            
            logger.info(f"Synced {saved_count} MCQ answers to PostgreSQL for candidate {candidate_id}")
            
            return {
                "success": failed_count == 0,
                "saved_count": saved_count,
                "failed_count": failed_count,
                "failed_questions": failed_questions,
                "total_score": total_score,
                "correct_answers": correct_answers,
                "incorrect_answers": incorrect_answers
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing MCQ answers to PostgreSQL for candidate {candidate_id}: {str(e)}")
            return {
                "success": False,
                "saved_count": saved_count,
                "failed_count": failed_count + len(mcq_answers) - saved_count,
                "error": str(e)
            }
    
    def sync_coding_answers_to_postgresql(self, candidate_id: str, coding_answers: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync Coding answers from Redis to PostgreSQL.
        
        Args:
            candidate_id: UUID of the candidate
            coding_answers: Dictionary with coding answers from Redis
            
        Returns:
            Dictionary with sync results
        """
        # TODO: Implement coding answers sync
        # This depends on the InterviewCoding model structure
        logger.info(f"Syncing coding answers for candidate {candidate_id} (to be implemented)")
        return {
            "success": True,
            "message": "Coding answers sync to be implemented"
        }
    
    def sync_system_design_to_postgresql(self, candidate_id: str, system_design_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sync System Design data from Redis to PostgreSQL.
        
        Args:
            candidate_id: UUID of the candidate
            system_design_data: Dictionary with system design data from Redis
            
        Returns:
            Dictionary with sync results
        """
        # TODO: Implement system design sync
        # This depends on the InterviewSystemDesign model structure
        logger.info(f"Syncing system design data for candidate {candidate_id} (to be implemented)")
        return {
            "success": True,
            "message": "System design sync to be implemented"
        }
    
    def sync_all_answers_to_postgresql(self, candidate_id: str) -> Dict[str, Any]:
        """
        Sync all answers (MCQ, Coding, System Design) from Redis to PostgreSQL.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Dictionary with sync results for all sections
        """
        try:
            answers = self.get_answers_from_redis(candidate_id)
            progress = self.get_progress_from_redis(candidate_id)
            
            results = {
                "mcq": {"success": False},
                "coding": {"success": False},
                "system_design": {"success": False},
                "progress": {}
            }
            
            # Sync MCQ answers
            if answers.get("mcq"):
                results["mcq"] = self.sync_mcq_answers_to_postgresql(candidate_id, answers["mcq"])
            
            # Sync Coding answers
            if answers.get("coding"):
                results["coding"] = self.sync_coding_answers_to_postgresql(candidate_id, answers["coding"])
            
            # Sync System Design data
            if answers.get("system_design"):
                results["system_design"] = self.sync_system_design_to_postgresql(candidate_id, answers["system_design"])
            
            # Update progress in TestSession table
            if progress:
                candidate = self.db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
                if candidate:
                    test_session = candidate.test_session
                    if not test_session:
                        test_session = TestSession(candidate_id=candidate_id)
                        self.db.add(test_session)
                        self.db.flush()
                    
                    if progress.get("sections_completed"):
                        test_session.sections_completed = progress["sections_completed"]
                    if progress.get("section_timings"):
                        test_session.section_timings = progress["section_timings"]
                    self.db.commit()
                    results["progress"] = {"success": True}
            
            # Update last_activity
            candidate = self.db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
            if candidate and candidate.test_session:
                candidate.test_session.last_activity = datetime.utcnow()
                self.db.commit()
            
            logger.info(f"Synced all answers to PostgreSQL for candidate {candidate_id}")
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error syncing all answers to PostgreSQL for candidate {candidate_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

