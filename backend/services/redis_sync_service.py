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
                answers_dict = json.loads(data)
                sections_found = list(answers_dict.keys())
                logger.info(f"[DATA_SOURCE] ✅ Fetched answers from REDIS for candidate {candidate_id} - Sections: {sections_found}")
                return answers_dict
            else:
                logger.info(f"[DATA_SOURCE] ⚠️ No answers found in REDIS for candidate {candidate_id} - returning empty dict")
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
                progress_dict = json.loads(data)
                logger.info(f"[DATA_SOURCE] ✅ Fetched progress from REDIS for candidate {candidate_id}")
                return progress_dict
            else:
                logger.info(f"[DATA_SOURCE] ⚠️ No progress found in REDIS for candidate {candidate_id} - returning empty dict")
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
        try:
            from models.interview_system_design import InterviewSystemDesign
            import json
            
            synced_count = 0
            failed_count = 0
            
            # Get all system design sessions for this candidate from Redis
            pattern = f"candidate:{candidate_id}:system_design:*:session"
            session_keys = self.redis_client.keys(pattern)
            
            for redis_key in session_keys:
                try:
                    # Parse question_uuid from key: candidate:{candidate_id}:system_design:{question_uuid}:session
                    parts = redis_key.split(":")
                    question_uuid = parts[3]
                    
                    # Verify candidate exists before syncing
                    candidate_exists = self.db.query(Candidate).filter(
                        Candidate.candidate_id == candidate_id
                    ).first()
                    
                    if not candidate_exists:
                        logger.warning(f"Candidate {candidate_id} not found in database, skipping system design sync for {question_uuid}")
                        failed_count += 1
                        continue
                    
                    # Get session data from Redis
                    session_data = self.redis_client.get(redis_key)
                    if not session_data:
                        continue
                    
                    session_dict = json.loads(session_data)
                    
                    # Get or create interview_system_design record
                    db_record = self.db.query(InterviewSystemDesign).filter(
                        InterviewSystemDesign.candidate_id == candidate_id,
                        InterviewSystemDesign.question_uuid == question_uuid
                    ).first()
                    
                    # Parse timestamps
                    last_activity = None
                    if session_dict.get("last_activity_time"):
                        try:
                            if isinstance(session_dict["last_activity_time"], str):
                                last_activity = datetime.fromisoformat(session_dict["last_activity_time"].replace('Z', '+00:00'))
                            else:
                                last_activity = datetime.fromtimestamp(session_dict["last_activity_time"])
                        except:
                            pass
                    
                    last_drawing = None
                    if session_dict.get("last_drawing_activity_time"):
                        try:
                            if isinstance(session_dict["last_drawing_activity_time"], str):
                                last_drawing = datetime.fromisoformat(session_dict["last_drawing_activity_time"].replace('Z', '+00:00'))
                            else:
                                last_drawing = datetime.fromtimestamp(session_dict["last_drawing_activity_time"])
                        except:
                            pass
                    
                    # Collect chat messages from Redis
                    chat_key = f"candidate:{candidate_id}:system_design:{question_uuid}:chat"
                    cached_chat = self.redis_client.lrange(chat_key, 0, -1)
                    chat_messages = []
                    
                    if cached_chat:
                        for msg_json in cached_chat:
                            try:
                                msg = json.loads(msg_json)
                                chat_messages.append({
                                    "role": msg.get("role", "user"),
                                    "content": msg.get("content", ""),
                                    "timestamp": msg.get("timestamp") or datetime.utcnow().isoformat()
                                })
                            except Exception as e:
                                logger.warning(f"Error parsing chat message: {e}")
                                continue
                    
                    # Merge with existing chat messages (avoid duplicates)
                    if db_record and db_record.chat_messages:
                        existing_contents = {(m.get("content"), m.get("role")) for m in db_record.chat_messages}
                        for msg in chat_messages:
                            if (msg.get("content"), msg.get("role")) not in existing_contents:
                                db_record.chat_messages.append(msg)
                        chat_messages = db_record.chat_messages
                    
                    if not db_record:
                        # Create new record
                        # Note: Do not set updated_at - let database trigger handle it
                        db_record = InterviewSystemDesign(
                            candidate_id=candidate_id,
                            question_uuid=question_uuid,
                            current_canvas=session_dict.get("current_canvas"),
                            previous_canvas=session_dict.get("previous_canvas"),
                            chat_messages=chat_messages,
                            last_activity_time=last_activity,
                            last_drawing_activity_time=last_drawing,
                            prompt_history=session_dict.get("prompt_history", []),
                            milestones=session_dict.get("milestones", {}),
                            last_canvas_hash=session_dict.get("last_canvas_hash"),
                            status='in_progress' if session_dict.get("current_canvas") else 'assigned'
                        )
                        self.db.add(db_record)
                    else:
                        # Update existing record (preserve score and diagram)
                        # Note: Do not set updated_at - let database trigger handle it automatically
                        if session_dict.get("current_canvas"):
                            db_record.current_canvas = session_dict.get("current_canvas")
                        if session_dict.get("previous_canvas"):
                            db_record.previous_canvas = session_dict.get("previous_canvas")
                        db_record.chat_messages = chat_messages
                        if last_activity and (not db_record.last_activity_time or last_activity > db_record.last_activity_time):
                            db_record.last_activity_time = last_activity
                        if last_drawing:
                            db_record.last_drawing_activity_time = last_drawing
                        if session_dict.get("prompt_history"):
                            db_record.prompt_history = session_dict.get("prompt_history", [])
                        if session_dict.get("milestones"):
                            db_record.milestones = session_dict.get("milestones", {})
                        if session_dict.get("last_canvas_hash"):
                            db_record.last_canvas_hash = session_dict.get("last_canvas_hash")
                        # Update status if not already evaluated/submitted
                        if db_record.status not in ['submitted', 'evaluated']:
                            db_record.status = 'in_progress' if session_dict.get("current_canvas") else 'assigned'
                    
                    self.db.commit()
                    synced_count += 1
                    logger.debug(f"Synced system design session: {candidate_id}:{question_uuid}")
                    
                except Exception as e:
                    logger.error(f"Error syncing system design session {redis_key}: {str(e)}")
                    self.db.rollback()
                    failed_count += 1
                    continue
            
            logger.info(f"Synced {synced_count} system design sessions to PostgreSQL for candidate {candidate_id}")
            
            return {
                "success": failed_count == 0,
                "synced_count": synced_count,
                "failed_count": failed_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing system design data for candidate {candidate_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def sync_all_system_design_sessions(self) -> Dict[str, Any]:
        """
        Sync all active system design sessions from Redis to PostgreSQL.
        Finds all sessions in Redis and syncs them.
        
        Returns:
            Dictionary with sync results
        """
        try:
            # Find all system design session keys in Redis
            pattern = "candidate:*:system_design:*:session"
            session_keys = self.redis_client.keys(pattern)
            
            synced_count = 0
            failed_count = 0
            failed_sessions = []
            
            # Group by candidate_id to use existing sync method
            candidates_to_sync = set()
            for redis_key in session_keys:
                try:
                    # Parse candidate_id from key
                    # Format: candidate:{candidate_id}:system_design:{question_uuid}:session
                    parts = redis_key.split(":")
                    if len(parts) >= 2:
                        candidate_id = parts[1]
                        candidates_to_sync.add(candidate_id)
                except Exception as e:
                    logger.warning(f"Error parsing session key {redis_key}: {e}")
                    continue
            
            # Sync all sessions for each candidate
            for candidate_id in candidates_to_sync:
                try:
                    result = self.sync_system_design_to_postgresql(candidate_id, {})
                    if result.get("success"):
                        synced_count += result.get("synced_count", 0)
                        failed_count += result.get("failed_count", 0)
                    else:
                        failed_count += 1
                        failed_sessions.append(candidate_id)
                except Exception as e:
                    logger.error(f"Error syncing candidate {candidate_id}: {e}")
                    failed_count += 1
                    failed_sessions.append(candidate_id)
            
            logger.info(f"Synced {synced_count} system design sessions, {failed_count} failed")
            
            return {
                "success": failed_count == 0,
                "synced_count": synced_count,
                "failed_count": failed_count,
                "failed_sessions": failed_sessions
            }
            
        except Exception as e:
            logger.error(f"Error syncing all system design sessions: {e}")
            return {
                "success": False,
                "error": str(e)
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
            logger.info(f"[DATA_SOURCE] 🔄 Starting sync from REDIS to POSTGRESQL for candidate {candidate_id}")
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
                logger.info(f"[DATA_SOURCE] 📥 Syncing {len(answers['mcq'])} MCQ answers from REDIS to POSTGRESQL for candidate {candidate_id}")
                results["mcq"] = self.sync_mcq_answers_to_postgresql(candidate_id, answers["mcq"])
                if results["mcq"].get("success"):
                    logger.info(f"[DATA_SOURCE] ✅ Synced {results['mcq'].get('saved_count', 0)} MCQ answers to POSTGRESQL for candidate {candidate_id}")
                else:
                    logger.warning(f"[DATA_SOURCE] ❌ Failed to sync MCQ answers to POSTGRESQL for candidate {candidate_id}")
            else:
                logger.info(f"[DATA_SOURCE] ℹ️ No MCQ answers in REDIS for candidate {candidate_id} - skipping sync")
            
            # Sync Coding answers
            if answers.get("coding"):
                logger.info(f"[DATA_SOURCE] 📥 Syncing coding answers from REDIS to POSTGRESQL for candidate {candidate_id}")
                results["coding"] = self.sync_coding_answers_to_postgresql(candidate_id, answers["coding"])
            else:
                logger.info(f"[DATA_SOURCE] ℹ️ No coding answers in REDIS for candidate {candidate_id} - skipping sync")
            
            # Sync System Design data (from Redis session keys, not answers key)
            # System design sessions are stored as: candidate:{candidate_id}:system_design:{question_uuid}:session
            logger.info(f"[DATA_SOURCE] 📥 Syncing system design data from REDIS to POSTGRESQL for candidate {candidate_id}")
            results["system_design"] = self.sync_system_design_to_postgresql(candidate_id, {})
            
            # Update progress in TestSession table
            if progress:
                logger.info(f"[DATA_SOURCE] 📥 Syncing progress data from REDIS to POSTGRESQL for candidate {candidate_id}")
                candidate = self.db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
                if candidate:
                    # Query test_session directly to avoid relationship issues (InstrumentedList)
                    test_session = self.db.query(TestSession).filter(
                        TestSession.candidate_id == candidate_id
                    ).first()
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
                    logger.info(f"[DATA_SOURCE] ✅ Synced progress data to POSTGRESQL for candidate {candidate_id}")
            else:
                logger.info(f"[DATA_SOURCE] ℹ️ No progress data in REDIS for candidate {candidate_id} - skipping sync")
            
            # Update last_activity
            candidate = self.db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
            if candidate:
                # Query test_session directly to avoid relationship issues (InstrumentedList)
                test_session = self.db.query(TestSession).filter(
                    TestSession.candidate_id == candidate_id
                ).first()
                if test_session:
                    test_session.last_activity = datetime.utcnow()
                    self.db.commit()
            
            logger.info(f"[DATA_SOURCE] ✅ Completed sync from REDIS to POSTGRESQL for candidate {candidate_id}")
            
            return {
                "success": True,
                "results": results
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"[DATA_SOURCE] ❌ Error syncing all answers to PostgreSQL for candidate {candidate_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }

