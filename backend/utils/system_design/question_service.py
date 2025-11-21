"""
Question Service Layer
Handles database operations for system design questions
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.system_design_question_bank import SystemDesignQuestionBank
import random


class QuestionService:
    """Service for managing system design questions"""
    
    def __init__(self, db_session: Session):
        self.db_session = db_session
    
    def get_question_by_id(self, uuid: str) -> Optional[SystemDesignQuestionBank]:
        """Get a question by UUID"""
        try:
            return self.db_session.query(SystemDesignQuestionBank).filter(
                SystemDesignQuestionBank.uuid == uuid
            ).first()
        except Exception as e:
            print(f"Error fetching question by ID: {e}")
            return None
    
    def get_questions_by_tag(self, tag: str) -> List[SystemDesignQuestionBank]:
        """Get all questions with a specific tag"""
        try:
            # For SQLite, tags is stored as JSON text, so we use LIKE
            # This works for both SQLite (TEXT) and PostgreSQL (JSONB)
            import json
            all_questions = self.db_session.query(SystemDesignQuestionBank).all()
            result = []
            for q in all_questions:
                try:
                    tags_list = json.loads(q.tags) if isinstance(q.tags, str) else q.tags
                    if tag in tags_list:
                        result.append(q)
                except (json.JSONDecodeError, TypeError):
                    # If tags is not valid JSON, skip
                    continue
            return result
        except Exception as e:
            print(f"Error fetching questions by tag: {e}")
            return []
    
    def get_all_questions(self) -> List[SystemDesignQuestionBank]:
        """Get all questions"""
        try:
            return self.db_session.query(SystemDesignQuestionBank).all()
        except Exception as e:
            print(f"Error fetching all questions: {e}")
            return []
    
    def get_random_question_by_tag(self, tag: str) -> Optional[SystemDesignQuestionBank]:
        """Get a random question by tag"""
        questions = self.get_questions_by_tag(tag)
        if questions:
            return random.choice(questions)
        return None
    
    def get_random_question(self) -> Optional[SystemDesignQuestionBank]:
        """Get a random question from all questions"""
        questions = self.get_all_questions()
        if questions:
            return random.choice(questions)
        return None
    
    def close(self):
        """Close database session"""
        if self.db_session:
            self.db_session.close()

