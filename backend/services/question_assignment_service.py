"""
Question Assignment Service for managing system design question assignments to candidates.
"""
import logging
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.candidate import Candidate
from models.recruiter_admin_candidate import RecruiterAdminCandidate
from models.job import Job
from models.interview_system_design import InterviewSystemDesign
from utils.system_design.question_service import QuestionService

logger = logging.getLogger(__name__)


class QuestionAssignmentService:
    """Service for assigning system design questions to candidates."""
    
    def __init__(self, db: Session):
        """Initialize service with database session."""
        self.db = db
        self.question_service = QuestionService(db)
    
    def get_assigned_question(self, candidate_id: str) -> Optional[str]:
        """
        Get the assigned question UUID for a candidate.
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Question UUID if assigned, None otherwise
        """
        try:
            assignment = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if assignment:
                logger.info(f"[QUESTION ASSIGNMENT] Found pre-assigned question for candidate {candidate_id}: {assignment.question_uuid}")
                return assignment.question_uuid
            logger.info(f"[QUESTION ASSIGNMENT] No pre-assigned question found for candidate {candidate_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching assigned question for candidate {candidate_id}: {e}")
            return None
    
    def select_question_by_job_role(self, candidate_id: str) -> Optional[str]:
        """
        Select a question based on candidate's job role.
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Selected question UUID or None
        """
        try:
            # Get candidate
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                return None
            
            # Get candidate's job assignment
            assignment = self.db.query(RecruiterAdminCandidate).filter(
                RecruiterAdminCandidate.candidate_id == candidate_id
            ).first()
            
            if not assignment:
                # No job assignment, use default tag
                logger.info(f"[QUESTION ASSIGNMENT] No job assignment for candidate {candidate_id}, using default tag: normal_hld")
                question = self.question_service.get_random_question_by_tag("normal_hld")
                if question:
                    logger.info(f"[QUESTION ASSIGNMENT] Selected default question UUID: {question.uuid}")
                return question.uuid if question else None
            
            # Get job details
            job = self.db.query(Job).filter(
                Job.job_id == assignment.job_id
            ).first()
            
            if not job:
                # Job not found, use default tag
                logger.info(f"[QUESTION ASSIGNMENT] Job not found for candidate {candidate_id}, using default tag: normal_hld")
                question = self.question_service.get_random_question_by_tag("normal_hld")
                if question:
                    logger.info(f"[QUESTION ASSIGNMENT] Selected default question UUID: {question.uuid}")
                return question.uuid if question else None
            
            # Map job_role to question tag
            job_role_lower = job.job_role.lower()
            
            # Determine tag based on job role
            if any(keyword in job_role_lower for keyword in [
                "ml", "machine learning", "data scientist", "ai engineer", 
                "llm", "artificial intelligence", "deep learning"
            ]):
                tag = "agentic_ai_hld"
            elif any(keyword in job_role_lower for keyword in [
                "backend", "engineer", "software", "developer", "system"
            ]):
                tag = "normal_hld"
            elif any(keyword in job_role_lower for keyword in [
                "frontend", "ui", "ux", "web developer"
            ]):
                tag = "normal_hld"  # Frontend questions can use normal_hld
            else:
                tag = "normal_hld"  # Default fallback
            
            logger.info(f"[QUESTION ASSIGNMENT] Auto-selecting question for candidate {candidate_id} with job role '{job.job_role}' -> tag: {tag}")
            
            # Get random question by tag
            question = self.question_service.get_random_question_by_tag(tag)
            
            if question:
                logger.info(f"[QUESTION ASSIGNMENT] Selected question UUID: {question.uuid} (tag: {tag})")
                return question.uuid
            
            # If no question found with tag, try default
            logger.warning(f"[QUESTION ASSIGNMENT] No question found with tag '{tag}' for candidate {candidate_id}, trying default tag")
            question = self.question_service.get_random_question_by_tag("normal_hld")
            if question:
                logger.info(f"[QUESTION ASSIGNMENT] Selected fallback question UUID: {question.uuid}")
            return question.uuid if question else None
            
        except Exception as e:
            logger.error(f"Error selecting question by job role for candidate {candidate_id}: {e}")
            # Fallback to default
            question = self.question_service.get_random_question_by_tag("normal_hld")
            if question:
                logger.info(f"[QUESTION ASSIGNMENT] Selected error-fallback question UUID: {question.uuid}")
            return question.uuid if question else None
    
    def assign_question_to_candidate(
        self, 
        candidate_id: str, 
        question_uuid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assign a question to a candidate.
        
        Args:
            candidate_id: Candidate UUID
            question_uuid: Optional question UUID. If not provided, auto-selects based on job role.
            
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
            
            # Determine question UUID
            if not question_uuid:
                # Auto-select based on job role
                logger.info(f"[QUESTION ASSIGNMENT] Auto-selecting question for candidate {candidate_id} based on job role")
                question_uuid = self.select_question_by_job_role(candidate_id)
                
                if not question_uuid:
                    logger.error(f"[QUESTION ASSIGNMENT] Failed to auto-select question for candidate {candidate_id}")
                    return {
                        "success": False,
                        "message": "Failed to auto-select question. No questions available."
                    }
            else:
                # Verify question exists
                logger.info(f"[QUESTION ASSIGNMENT] Using provided question UUID {question_uuid} for candidate {candidate_id}")
                question = self.question_service.get_question_by_id(question_uuid)
                if not question:
                    logger.error(f"[QUESTION ASSIGNMENT] Question UUID {question_uuid} not found for candidate {candidate_id}")
                    return {
                        "success": False,
                        "message": f"Question with UUID {question_uuid} not found"
                    }
                else:
                    logger.info(f"[QUESTION ASSIGNMENT] Verified question UUID {question_uuid} exists")
            
            # Check if assignment already exists
            existing_assignment = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if existing_assignment:
                # Check if test has started (score is not NULL)
                if existing_assignment.score is not None:
                    logger.warning(f"[QUESTION ASSIGNMENT] Cannot reassign question for candidate {candidate_id} - test already completed")
                    return {
                        "success": False,
                        "message": "Cannot reassign question. Candidate has already completed the test."
                    }
                
                # Update existing assignment
                old_uuid = existing_assignment.question_uuid
                existing_assignment.question_uuid = question_uuid
                self.db.commit()
                
                logger.info(f"[QUESTION ASSIGNMENT] ✅ REASSIGNED question for candidate {candidate_id}: {old_uuid} -> {question_uuid}")
                
                return {
                    "success": True,
                    "message": f"Question reassigned successfully. New question UUID: {question_uuid}",
                    "question_uuid": question_uuid
                }
            else:
                # Create new assignment
                new_assignment = InterviewSystemDesign(
                    candidate_id=candidate_id,
                    question_uuid=question_uuid,
                    score=None,
                    diagram=None
                )
                self.db.add(new_assignment)
                self.db.commit()
                
                # Get question details for logging
                question = self.question_service.get_question_by_id(question_uuid)
                question_text = question.question[:100] + "..." if question and len(question.question) > 100 else (question.question if question else "N/A")
                
                logger.info(f"[QUESTION ASSIGNMENT] ✅ ASSIGNED question to candidate {candidate_id}")
                logger.info(f"[QUESTION ASSIGNMENT]    Question UUID: {question_uuid}")
                logger.info(f"[QUESTION ASSIGNMENT]    Question: {question_text}")
                
                return {
                    "success": True,
                    "message": f"Question assigned successfully. Question UUID: {question_uuid}",
                    "question_uuid": question_uuid
                }
                
        except Exception as e:
            self.db.rollback()
            return {
                "success": False,
                "message": f"Error assigning question: {str(e)}"
            }
    
    def get_assigned_question_details(self, candidate_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full details of assigned question for a candidate.
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Dictionary with question details or None
        """
        try:
            assignment = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if not assignment:
                return None
            
            # Get question details
            question = self.question_service.get_question_by_id(assignment.question_uuid)
            
            if not question:
                return None
            
            return {
                "candidate_id": candidate_id,
                "question_uuid": assignment.question_uuid,
                "question": question.question
            }
            
        except Exception as e:
            print(f"Error fetching assigned question details: {e}")
            return None

