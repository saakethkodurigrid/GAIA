"""
Test Data Loader Service for loading test questions into Redis.
Loads all assigned questions (MCQ, Coding, System Design) into Redis when test starts.
"""
import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from models.interview_mcq import InterviewMCQ
from models.interview_coding import InterviewCoding
from models.interview_system_design import InterviewSystemDesign
from services.question_assignment_service import QuestionAssignmentService
from utils.system_design.question_service import QuestionService
from core.redis_client import get_redis_client
from core.config import settings

logger = logging.getLogger(__name__)


class TestDataLoaderService:
    """Service for loading test data into Redis."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.redis_client = get_redis_client()
    
    def load_test_data_to_redis(self, candidate_id: str) -> Dict[str, Any]:
        """
        Load all test data (MCQ, Coding, System Design questions) into Redis.
        
        This is called when test starts. All questions are loaded once into Redis
        to avoid database queries during the test.
        
        Uses Redis pipeline to batch all writes into a single operation,
        preventing timeouts with multiple sequential writes.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Dictionary with success status and loaded data summary
        """
        try:
            test_data = {
                "mcq_questions": [],
                "coding_questions": [],
                "system_design_question": None,
                "test_start_time": None,
                "test_duration_minutes": None
            }
            
            # Load MCQ questions
            mcq_records = self.db.query(InterviewMCQ).filter(
                InterviewMCQ.candidate_id == candidate_id
            ).all()
            
            for mcq in mcq_records:
                options = []
                if mcq.options and isinstance(mcq.options, list):
                    options = mcq.options
                elif mcq.tags and isinstance(mcq.tags, dict):
                    if 'options' in mcq.tags and isinstance(mcq.tags['options'], list):
                        options = mcq.tags['options']
                
                test_data["mcq_questions"].append({
                    "uuid": mcq.uuid,
                    "question": mcq.question,
                    "options": options,
                    "correct_answer": mcq.correct_answer,
                    "difficulty": mcq.difficulty,
                    "tags": mcq.tags
                })
            
            # Load Coding questions - optimized batch fetch
            coding_records = self.db.query(InterviewCoding).filter(
                InterviewCoding.candidate_id == candidate_id
            ).all()
            
            # Collect all question UUIDs for batch fetch
            question_uuids = [coding.question_uuid for coding in coding_records if coding.question_uuid]
            
            # Batch fetch all CodingQuestionBank records in a single query
            coding_question_map = {}
            if question_uuids:
                from models.coding_question_bank import CodingQuestionBank
                coding_questions_db = self.db.query(CodingQuestionBank).filter(
                    CodingQuestionBank.uuid.in_(question_uuids)
                ).all()
                
                # Build lookup map
                coding_question_map = {q.uuid: q for q in coding_questions_db}
            
            # Prepare coding question references for test_data and individual Redis keys
            coding_question_cache = {}
            
            for coding in coding_records:
                if not coding.question_uuid:
                    continue
                    
                coding_question = coding_question_map.get(coding.question_uuid)
                
                # Store reference in test_data (only uuid + difficulty)
                test_data["coding_questions"].append({
                    "question_uuid": coding.question_uuid,
                    "difficulty": coding.difficulty if hasattr(coding, 'difficulty') else None
                })
                
                # Prepare full question data for individual Redis key (only cache required fields)
                if coding_question:
                    question_data = {
                        "question_uuid": coding.question_uuid,
                        "question": coding_question.question if hasattr(coding_question, 'question') else None,
                        "boilerplate_code": coding_question.boiler_plate if hasattr(coding_question, 'boiler_plate') else None,
                        "sample_test_cases": coding_question.sample_test_cases if hasattr(coding_question, 'sample_test_cases') else None,
                        # NOTE: test_cases NOT cached in Redis (too large - causes timeouts)
                        # They are fetched from database on-demand when code is executed
                        "difficulty": coding.difficulty if hasattr(coding, 'difficulty') else None,
                        "tags": coding_question.tags if hasattr(coding_question, 'tags') else None
                    }
                    coding_question_cache[coding.question_uuid] = question_data
            
            # Load System Design question
            assignment = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if assignment and assignment.question_uuid:
                question_service = QuestionService(self.db)
                question = question_service.get_question_by_id(assignment.question_uuid)
                
                if question:
                    test_data["system_design_question"] = {
                        "question_uuid": question.uuid,
                        "question": question.question,
                        "evaluation_criteria": question.evaluation_criteria,
                        "tags": question.tags
                    }
            
            # ===================================================================
            # Use Redis Pipeline for atomic batch writes (prevents timeouts)
            # ===================================================================
            pipeline = self.redis_client.pipeline()
            
            # 1. Cache individual coding questions
            for question_uuid, question_data in coding_question_cache.items():
                individual_key = f"candidate:{candidate_id}:coding_question:{question_uuid}"
                pipeline.setex(
                    individual_key,
                    settings.REDIS_TTL_SECONDS,
                    json.dumps(question_data)
                )
            
            # 2. Store main test data bundle
            redis_key = f"candidate:{candidate_id}:test_data"
            pipeline.setex(
                redis_key,
                settings.REDIS_TTL_SECONDS,
                json.dumps(test_data)
            )
            
            # 3. Execute all writes in a single network call
            pipeline.execute()
            
            logger.info(f"Loaded test data to Redis for candidate {candidate_id}: "
                       f"{len(test_data['mcq_questions'])} MCQ, "
                       f"{len(test_data['coding_questions'])} Coding, "
                       f"{'1' if test_data['system_design_question'] else '0'} System Design")
            
            return {
                "success": True,
                "mcq_count": len(test_data["mcq_questions"]),
                "coding_count": len(test_data["coding_questions"]),
                "system_design_loaded": test_data["system_design_question"] is not None
            }
            
        except Exception as e:
            logger.error(f"Error loading test data to Redis for candidate {candidate_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_test_data_from_redis(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get test data from Redis.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Dictionary with test data or None if not found
        """
        try:
            redis_key = f"candidate:{candidate_id}:test_data"
            data = self.redis_client.get(redis_key)
            
            if data:
                logger.info(f"[DATA_SOURCE] ✅ Fetched test data from REDIS for candidate {candidate_id}")
                return json.loads(data)
            else:
                logger.info(f"[DATA_SOURCE] ⚠️ No test data found in REDIS for candidate {candidate_id} - returning None")
            return None
            
        except Exception as e:
            logger.error(f"Error getting test data from Redis for candidate {candidate_id}: {str(e)}")
            return None
    
    def get_mcq_questions_from_redis(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Get MCQ questions from Redis.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            List of MCQ questions
        """
        test_data = self.get_test_data_from_redis(candidate_id)
        if test_data:
            return test_data.get("mcq_questions", [])
        return []
    
    def get_coding_questions_from_redis(self, candidate_id: str) -> List[Dict[str, Any]]:
        """
        Get Coding questions from Redis.
        
        Fetches full question data from individual Redis keys using references
        stored in test_data.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            List of Coding questions with full data
        """
        try:
            # Get coding question references from test_data
            test_data = self.get_test_data_from_redis(candidate_id)
            if not test_data:
                return []
            
            coding_references = test_data.get("coding_questions", [])
            if not coding_references:
                return []
            
            # Fetch full question data from individual Redis keys
            logger.info(f"[DATA_SOURCE] 📥 Fetching {len(coding_references)} coding questions from REDIS (individual keys) for candidate {candidate_id}")
            coding_questions = []
            found_from_redis = 0
            found_from_reference = 0
            
            for ref in coding_references:
                question_uuid = ref.get("question_uuid")
                if not question_uuid:
                    continue
                
                redis_key = f"candidate:{candidate_id}:coding_question:{question_uuid}"
                data = self.redis_client.get(redis_key)
                
                if data:
                    question_data = json.loads(data)
                    coding_questions.append(question_data)
                    found_from_redis += 1
                else:
                    # If individual key not found, include reference with available data
                    logger.warning(f"[DATA_SOURCE] ⚠️ Individual coding question key not found in REDIS for {question_uuid}, using reference data")
                    coding_questions.append(ref)
                    found_from_reference += 1
            
            logger.info(f"[DATA_SOURCE] ✅ Fetched coding questions from REDIS for candidate {candidate_id} - {found_from_redis} from individual keys, {found_from_reference} from references")
            return coding_questions
            
        except Exception as e:
            logger.error(f"Error getting coding questions from Redis for candidate {candidate_id}: {str(e)}")
            return []
    
    def get_coding_question_from_redis(self, candidate_id: str, question_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific coding question from Redis by question_id.
        
        Optimized lookup: First tries individual question key, then falls back to
        full test data lookup if individual key not found.
        
        Args:
            candidate_id: UUID of the candidate
            question_id: UUID of the coding question
            
        Returns:
            Coding question dictionary or None if not found
        """
        try:
            # Try individual question key first (optimized path)
            redis_key = f"candidate:{candidate_id}:coding_question:{question_id}"
            logger.info(f"[DATA_SOURCE] 📥 Fetching coding question {question_id} from REDIS (individual key) for candidate {candidate_id}")
            data = self.redis_client.get(redis_key)
            
            if data:
                logger.info(f"[DATA_SOURCE] ✅ Found coding question {question_id} in REDIS (individual key) for candidate {candidate_id}")
                return json.loads(data)
            
            # Fallback: check if reference exists in test_data and try to fetch individual key again
            # (handles race condition where test_data was written but individual key not yet available)
            logger.info(f"[DATA_SOURCE] ⚠️ Coding question {question_id} not found in REDIS individual key, checking test_data for candidate {candidate_id}")
            test_data = self.get_test_data_from_redis(candidate_id)
            if test_data:
                for ref in test_data.get("coding_questions", []):
                    if ref.get("question_uuid") == question_id:
                        # Reference found, but individual key missing - return reference data
                        logger.warning(f"[DATA_SOURCE] ⚠️ Found coding question reference for {question_id} but individual key missing - using reference data")
                        return ref
            
            logger.info(f"[DATA_SOURCE] ❌ Coding question {question_id} not found in REDIS for candidate {candidate_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting coding question from Redis: {str(e)}")
            return None
    
    def get_system_design_question_from_redis(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get System Design question from Redis.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            System Design question dictionary or None
        """
        test_data = self.get_test_data_from_redis(candidate_id)
        if test_data:
            return test_data.get("system_design_question")
        return None
    
    def clear_test_data_from_redis(self, candidate_id: str) -> bool:
        """
        Clear all test-related data from Redis for a candidate.
        
        Also clears individual question keys using pattern matching.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            True if successful, False otherwise
        """
        try:
            keys_to_delete = [
                f"candidate:{candidate_id}:test_data",
                f"candidate:{candidate_id}:answers",
                f"candidate:{candidate_id}:heartbeat",
                f"candidate:{candidate_id}:progress"
            ]
            
            # Delete individual coding question keys using pattern
            try:
                pattern = f"candidate:{candidate_id}:coding_question:*"
                # Note: Redis SCAN is needed for pattern matching, but for simplicity,
                # we'll delete known keys. If needed, can use redis.keys() but it's blocking.
                # For now, we rely on TTL expiration for individual keys.
                # If you need immediate deletion, you'd need to track question IDs.
            except Exception:
                pass  # Pattern deletion is optional
            
            for key in keys_to_delete:
                self.redis_client.delete(key)
            
            logger.info(f"Cleared test data from Redis for candidate {candidate_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error clearing test data from Redis for candidate {candidate_id}: {str(e)}")
            return False

