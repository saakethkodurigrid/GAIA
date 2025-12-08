"""
Coding Question Assignment Service for managing coding question assignments to candidates.
"""
import logging
import random
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models.candidate import Candidate
from models.coding_question_bank import CodingQuestionBank
from models.interview_coding import InterviewCoding

logger = logging.getLogger(__name__)


class CodingQuestionAssignmentService:
    """Service for assigning coding questions to candidates."""
    
    # Fixed question UUIDs when RANDOM_CODING_QUESTIONS is False
    FIXED_QUESTION_UUIDS = [
        "4d76d396-bf37-492d-86ba-2d611d2193c8",
        "13725261-21c9-424b-bced-e0be21078aeb",
        "cf43bce1-dfc7-4d42-904b-0d9461641076",
        "22c620aa-b462-4ca5-adee-74ef95598862"
    ]
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
    
    def get_random_questions_by_difficulty(
        self, 
        easy_count: int = 1,
        medium_count: int = 1,
        hard_count: int = 2
    ) -> Dict[str, List[CodingQuestionBank]]:
        """
        Get random questions by difficulty level.
        
        Args:
            easy_count: Number of easy questions to get
            medium_count: Number of medium questions to get
            hard_count: Number of hard questions to get
            
        Returns:
            Dictionary with keys 'easy', 'medium', 'hard' containing lists of questions
        """
        result = {
            'easy': [],
            'medium': [],
            'hard': []
        }
        
        try:
            # Get easy questions
            if easy_count > 0:
                easy_questions = self.db.query(CodingQuestionBank).filter(
                    CodingQuestionBank.difficulty == 'easy'
                ).all()
                if easy_questions:
                    selected = random.sample(easy_questions, min(easy_count, len(easy_questions)))
                    result['easy'] = selected
                    logger.info(f"Selected {len(selected)} easy question(s) from {len(easy_questions)} available")
                else:
                    logger.warning("No easy questions available in database")
            
            # Get medium questions
            if medium_count > 0:
                medium_questions = self.db.query(CodingQuestionBank).filter(
                    CodingQuestionBank.difficulty == 'medium'
                ).all()
                if medium_questions:
                    selected = random.sample(medium_questions, min(medium_count, len(medium_questions)))
                    result['medium'] = selected
                    logger.info(f"Selected {len(selected)} medium question(s) from {len(medium_questions)} available")
                else:
                    logger.warning("No medium questions available in database")
            
            # Get hard questions
            if hard_count > 0:
                hard_questions = self.db.query(CodingQuestionBank).filter(
                    CodingQuestionBank.difficulty == 'hard'
                ).all()
                if hard_questions:
                    selected = random.sample(hard_questions, min(hard_count, len(hard_questions)))
                    result['hard'] = selected
                    logger.info(f"Selected {len(selected)} hard question(s) from {len(hard_questions)} available")
                else:
                    logger.warning("No hard questions available in database")
            
        except Exception as e:
            logger.error(f"Error fetching questions by difficulty: {str(e)}")
        
        return result
    
    def assign_random_questions(self, candidate_id: str) -> Dict[str, Any]:
        """
        Assign random coding questions to candidate (1 easy, 1 medium, 2 hard).
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Verify candidate exists
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                return {
                    "success": False,
                    "message": f"Candidate with ID {candidate_id} not found"
                }
            
            # Get random questions by difficulty
            questions_by_difficulty = self.get_random_questions_by_difficulty(
                easy_count=1,
                medium_count=1,
                hard_count=2
            )
            
            # Collect all selected questions
            all_questions = []
            all_questions.extend(questions_by_difficulty['easy'])
            all_questions.extend(questions_by_difficulty['medium'])
            all_questions.extend(questions_by_difficulty['hard'])
            
            if len(all_questions) < 4:
                missing = 4 - len(all_questions)
                logger.warning(f"Only {len(all_questions)} questions available, expected 4. Missing {missing} question(s)")
            
            if not all_questions:
                return {
                    "success": False,
                    "message": "No coding questions available in database"
                }
            
            # Check for existing assignments
            existing_assignments = self.db.query(InterviewCoding).filter(
                InterviewCoding.candidate_id == candidate_id
            ).all()
            
            assigned_count = 0
            skipped_count = 0
            error_messages = []
            
            # Assign each question
            for question in all_questions:
                # Check if assignment already exists
                existing = next(
                    (a for a in existing_assignments if a.question_uuid == question.uuid),
                    None
                )
                
                if existing:
                    # Skip if already assigned
                    skipped_count += 1
                    logger.info(f"Question {question.uuid} already assigned to candidate {candidate_id}, skipping")
                    continue
                
                try:
                    # Create new assignment
                    new_assignment = InterviewCoding(
                        candidate_id=candidate_id,
                        question_uuid=question.uuid,
                        score=None,
                        test_cases_passed=None,
                        difficulty=question.difficulty
                    )
                    self.db.add(new_assignment)
                    assigned_count += 1
                    logger.info(f"Assigned coding question {question.uuid} (difficulty: {question.difficulty}) to candidate {candidate_id}")
                except Exception as e:
                    error_messages.append(f"Failed to assign question {question.uuid}: {str(e)}")
                    logger.error(f"Error assigning question {question.uuid}: {str(e)}")
            
            # Commit all assignments
            if assigned_count > 0:
                self.db.commit()
            
            # Build response message
            if assigned_count == 0 and skipped_count > 0:
                message = f"All {skipped_count} coding question(s) were already assigned to this candidate"
            elif assigned_count > 0:
                message = f"Assigned {assigned_count} coding question(s) to candidate"
                if skipped_count > 0:
                    message += f", {skipped_count} already assigned"
            else:
                message = "Failed to assign coding questions"
            
            if error_messages:
                message += f". Errors: {'; '.join(error_messages)}"
            
            return {
                "success": assigned_count > 0 or skipped_count >= 4,
                "message": message,
                "assigned_count": assigned_count,
                "skipped_count": skipped_count,
                "total_questions": len(all_questions)
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in assign_random_questions: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error assigning random coding questions: {str(e)}"
            }
    
    def assign_fixed_questions(self, candidate_id: str) -> Dict[str, Any]:
        """
        Assign fixed coding questions to candidate using predefined UUIDs.
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Dictionary with success status and message
        """
        try:
            # Verify candidate exists
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                return {
                    "success": False,
                    "message": f"Candidate with ID {candidate_id} not found"
                }
            
            # Check for existing assignments
            existing_assignments = self.db.query(InterviewCoding).filter(
                InterviewCoding.candidate_id == candidate_id
            ).all()
            
            existing_uuids = {a.question_uuid for a in existing_assignments}
            
            assigned_count = 0
            skipped_count = 0
            not_found_count = 0
            error_messages = []
            
            # Assign each fixed question UUID
            for question_uuid in self.FIXED_QUESTION_UUIDS:
                # Check if already assigned
                if question_uuid in existing_uuids:
                    skipped_count += 1
                    logger.info(f"Question {question_uuid} already assigned to candidate {candidate_id}, skipping")
                    continue
                
                # Verify question exists in database
                question = self.db.query(CodingQuestionBank).filter(
                    CodingQuestionBank.uuid == question_uuid
                ).first()
                
                if not question:
                    not_found_count += 1
                    error_messages.append(f"Question UUID {question_uuid} not found in database")
                    logger.warning(f"Question UUID {question_uuid} not found in database")
                    continue
                
                try:
                    # Create new assignment
                    new_assignment = InterviewCoding(
                        candidate_id=candidate_id,
                        question_uuid=question_uuid,
                        score=None,
                        test_cases_passed=None,
                        difficulty=question.difficulty
                    )
                    self.db.add(new_assignment)
                    assigned_count += 1
                    logger.info(f"Assigned fixed coding question {question_uuid} (difficulty: {question.difficulty}) to candidate {candidate_id}")
                except Exception as e:
                    error_messages.append(f"Failed to assign question {question_uuid}: {str(e)}")
                    logger.error(f"Error assigning question {question_uuid}: {str(e)}")
            
            # Commit all assignments
            if assigned_count > 0:
                self.db.commit()
            
            # Build response message
            if assigned_count == 0 and skipped_count > 0:
                message = f"All {skipped_count} coding question(s) were already assigned to this candidate"
            elif assigned_count > 0:
                message = f"Assigned {assigned_count} fixed coding question(s) to candidate"
                if skipped_count > 0:
                    message += f", {skipped_count} already assigned"
                if not_found_count > 0:
                    message += f", {not_found_count} not found in database"
            else:
                message = "Failed to assign fixed coding questions"
                if not_found_count > 0:
                    message += f". {not_found_count} question UUID(s) not found in database"
            
            if error_messages:
                message += f". Errors: {'; '.join(error_messages)}"
            
            return {
                "success": assigned_count > 0 or skipped_count >= 4,
                "message": message,
                "assigned_count": assigned_count,
                "skipped_count": skipped_count,
                "not_found_count": not_found_count
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error in assign_fixed_questions: {str(e)}", exc_info=True)
            return {
                "success": False,
                "message": f"Error assigning fixed coding questions: {str(e)}"
            }
    
    def assign_coding_questions_to_candidate(
        self, 
        candidate_id: str, 
        use_random: bool = True
    ) -> Dict[str, Any]:
        """
        Assign coding questions to candidate based on configuration.
        
        Args:
            candidate_id: Candidate UUID
            use_random: If True, assign random questions (1 easy, 1 medium, 2 hard)
                       If False, assign fixed question UUIDs
            
        Returns:
            Dictionary with success status and message
        """
        if use_random:
            logger.info(f"[CODING QUESTION ASSIGNMENT] Assigning random coding questions to candidate {candidate_id}")
            return self.assign_random_questions(candidate_id)
        else:
            logger.info(f"[CODING QUESTION ASSIGNMENT] Assigning fixed coding questions to candidate {candidate_id}")
            return self.assign_fixed_questions(candidate_id)

