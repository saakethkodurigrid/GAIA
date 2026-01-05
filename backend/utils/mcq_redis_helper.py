"""
Redis utility helper for MCQ draft answer management.
Provides functions for saving, retrieving, and clearing MCQ draft answers from Redis.
"""
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from core.redis_client import get_redis_client
from core.config import settings

logger = logging.getLogger(__name__)


def save_mcq_draft(candidate_id: str, answers: List[Dict[str, str]]) -> bool:
    """
    Save MCQ draft answers to Redis.
    
    Args:
        candidate_id: UUID of the candidate
        answers: List of answer dictionaries with 'question_uuid' and 'candidate_answer'
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        redis_key = f"mcq:{candidate_id}"
        
        # Prepare answers data with timestamp
        answers_data = {
            "answers": [
                {
                    "question_uuid": item.get("question_uuid"),
                    "candidate_answer": item.get("candidate_answer"),
                    "last_updated_at": datetime.utcnow().isoformat()
                }
                for item in answers
                if item.get("question_uuid") and item.get("candidate_answer")
            ],
            "last_updated_at": datetime.utcnow().isoformat()
        }
        
        # Save to Redis with TTL (24 hours default)
        redis_client.setex(
            redis_key,
            settings.REDIS_TTL_SECONDS,
            json.dumps(answers_data)
        )
        
        logger.info(f"Saved MCQ draft to Redis for candidate {candidate_id}: {len(answers_data['answers'])} answers")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to save MCQ draft to Redis for candidate {candidate_id}: {str(e)}")
        return False


def get_mcq_draft(candidate_id: str) -> Optional[List[Dict[str, str]]]:
    """
    Retrieve MCQ draft answers from Redis.
    
    Args:
        candidate_id: UUID of the candidate
        
    Returns:
        List of answer dictionaries with 'question_uuid' and 'candidate_answer', or None if not found
    """
    try:
        redis_client = get_redis_client()
        redis_key = f"mcq:{candidate_id}"
        redis_data = redis_client.get(redis_key)
        
        if not redis_data:
            return None
        
        redis_answers_dict = json.loads(redis_data)
        if isinstance(redis_answers_dict, dict) and "answers" in redis_answers_dict:
            return redis_answers_dict["answers"]
        
        return None
        
    except Exception as e:
        logger.warning(f"Failed to retrieve MCQ draft from Redis for candidate {candidate_id}: {str(e)}")
        return None


def clear_mcq_draft(candidate_id: str) -> bool:
    """
    Clear MCQ draft answers from Redis.
    
    Args:
        candidate_id: UUID of the candidate
        
    Returns:
        True if successful, False otherwise
    """
    try:
        redis_client = get_redis_client()
        redis_key = f"mcq:{candidate_id}"
        redis_client.delete(redis_key)
        logger.info(f"Cleared MCQ draft from Redis for candidate {candidate_id}")
        return True
        
    except Exception as e:
        logger.warning(f"Failed to clear MCQ draft from Redis for candidate {candidate_id}: {str(e)}")
        return False

