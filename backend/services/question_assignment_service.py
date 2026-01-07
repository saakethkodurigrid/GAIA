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
                return assignment.question_uuid.strip() if assignment.question_uuid else None
            logger.info(f"[QUESTION ASSIGNMENT] No pre-assigned question found for candidate {candidate_id}")
            return None
        except Exception as e:
            logger.error(f"Error fetching assigned question for candidate {candidate_id}: {e}")
            return None
    
    def select_question_by_job_role(self, candidate_id: str) -> Optional[str]:
        """
        Select a question based on candidate's job role.
        
        FAIL-FAST BEHAVIOR: This function requires complete job assignment data.
        Missing data (assignment, job, job_role) indicates a data integrity issue
        that must be fixed upstream. We do NOT silently fallback to defaults.
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Selected question UUID or None if data is missing or question selection fails
            
        Raises:
            ValueError: If required data (assignment, job, job_role) is missing
        """
        try:
            # Get candidate
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                error_msg = f"[QUESTION ASSIGNMENT] Data integrity error: Candidate {candidate_id} not found"
                logger.error(error_msg)
                raise ValueError(f"Candidate {candidate_id} not found")
            
            # Get candidate's job assignment - REQUIRED, no fallback
            assignment = self.db.query(RecruiterAdminCandidate).filter(
                RecruiterAdminCandidate.candidate_id == candidate_id
            ).first()
            
            if not assignment:
                error_msg = f"[QUESTION ASSIGNMENT] Data integrity error: No job assignment found for candidate {candidate_id}"
                logger.error(error_msg)
                raise ValueError(f"Job assignment not found for candidate {candidate_id}")
            
            # Get job details - REQUIRED, no fallback
            job = self.db.query(Job).filter(
                Job.job_id == assignment.job_id
            ).first()
            
            if not job:
                error_msg = f"[QUESTION ASSIGNMENT] Data integrity error: Job {assignment.job_id} not found for candidate {candidate_id}"
                logger.error(error_msg)
                raise ValueError(f"Job {assignment.job_id} not found for candidate {candidate_id}")
            
            # Job role is REQUIRED - no fallback
            if not job.job_role or not job.job_role.strip():
                error_msg = f"[QUESTION ASSIGNMENT] Data integrity error: Job role is missing or empty for job {job.job_id}, candidate {candidate_id}"
                logger.error(error_msg)
                raise ValueError(f"Job role is missing for job {job.job_id}")
            
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
                # Unknown job role - still use normal_hld but log it
                tag = "normal_hld"
                logger.info(f"[QUESTION ASSIGNMENT] Unknown job role '{job.job_role}' for candidate {candidate_id}, using tag: {tag}")
            
            logger.info(f"[QUESTION ASSIGNMENT] Selecting question for candidate {candidate_id} with job role '{job.job_role}' -> tag: {tag}")
            
            # Get random question by tag
            question = self.question_service.get_random_question_by_tag(tag)
            
            if question:
                logger.info(f"[QUESTION ASSIGNMENT] Selected question UUID: {question.uuid} (tag: {tag}, job_role: {job.job_role})")
                return question.uuid
            
            # If no question found with tag, this is a data issue - fail loudly
            error_msg = f"[QUESTION ASSIGNMENT] Data integrity error: No questions found with tag '{tag}' for candidate {candidate_id}"
            logger.error(error_msg)
            raise ValueError(f"No questions available with tag '{tag}'")
            
        except ValueError:
            # Re-raise ValueError (data integrity issues) - don't mask them
            raise
        except Exception as e:
            # Unexpected errors - log and re-raise, don't fallback
            error_msg = f"[QUESTION ASSIGNMENT] Unexpected error selecting question by job role for candidate {candidate_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            raise ValueError(f"Failed to select question: {str(e)}")
    
    def assign_question_to_candidate(
        self, 
        candidate_id: str
    ) -> Dict[str, Any]:
        """
        Assign a system design question to a candidate.
        
        IDEMPOTENT OPERATION: This function is safe to call multiple times.
        - If assignment already exists, returns existing assignment (no reassignment)
        - If no assignment exists, auto-selects question based on job role and creates new assignment
        - Designed to be safe against retries, double calls, and parallel execution
        
        This function enforces the invariant: one question per candidate, assigned only once.
        Questions are always auto-selected based on the candidate's job role.
        
        Args:
            candidate_id: Candidate UUID
            
        Returns:
            Dictionary with success status, message, and question_uuid
        """
        try:
            # IDEMPOTENCY CHECK: Check if assignment already exists FIRST
            # This ensures we never reassign, even in race conditions
            existing_assignment = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if existing_assignment:
                # Assignment already exists - return existing (idempotent behavior)
                # This handles: retries, double scheduling calls, parallel execution
                logger.info(
                    f"[QUESTION ASSIGNMENT] ✅ Already assigned - returning existing assignment for candidate {candidate_id}. "
                    f"Question UUID: {existing_assignment.question_uuid}, Status: {existing_assignment.status}"
                )
                
                # Get question details for logging
                question = self.question_service.get_question_by_id(existing_assignment.question_uuid)
                question_text = question.question[:100] + "..." if question and len(question.question) > 100 else (question.question if question else "N/A")
                
                logger.debug(
                    f"[QUESTION ASSIGNMENT] Existing assignment details - "
                    f"Candidate: {candidate_id}, Question UUID: {existing_assignment.question_uuid}, "
                    f"Question: {question_text}"
                )
                
                return {
                    "success": True,
                    "message": f"Question already assigned. Question UUID: {existing_assignment.question_uuid}",
                    "question_uuid": existing_assignment.question_uuid
                }
            
            # No existing assignment - proceed with new assignment
            # Verify candidate exists
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                error_msg = f"[QUESTION ASSIGNMENT] Data integrity error: Candidate {candidate_id} not found"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": f"Candidate with ID {candidate_id} not found"
                }
            
            # Auto-select question based on job role (will fail-fast if data is missing)
            logger.info(f"[QUESTION ASSIGNMENT] Assigning for the first time - auto-selecting question for candidate {candidate_id} based on job role")
            try:
                question_uuid = self.select_question_by_job_role(candidate_id)
            except ValueError as e:
                # Data integrity error from select_question_by_job_role
                error_msg = f"[QUESTION ASSIGNMENT] Failed to auto-select question for candidate {candidate_id}: {str(e)}"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": f"Failed to auto-select question: {str(e)}"
                }
            
            if not question_uuid:
                error_msg = f"[QUESTION ASSIGNMENT] Failed to auto-select question for candidate {candidate_id}: select_question_by_job_role returned None"
                logger.error(error_msg)
                return {
                    "success": False,
                    "message": "Failed to auto-select question. No questions available."
                }
            
            # Create new assignment (idempotency check already passed above)
            # Handle potential race condition: another thread might have created assignment between check and create
            try:
                new_assignment = InterviewSystemDesign(
                    candidate_id=candidate_id,
                    question_uuid=question_uuid,
                    score=None,
                    diagram=None,
                    status='assigned'
                )
                self.db.add(new_assignment)
                self.db.commit()
                
                # Get question details for logging
                question = self.question_service.get_question_by_id(question_uuid)
                question_text = question.question[:100] + "..." if question and len(question.question) > 100 else (question.question if question else "N/A")
                
                logger.info(f"[QUESTION ASSIGNMENT] ✅ ASSIGNED question to candidate {candidate_id} for the first time")
                logger.info(f"[QUESTION ASSIGNMENT]    Candidate ID: {candidate_id}")
                logger.info(f"[QUESTION ASSIGNMENT]    Question UUID: {question_uuid}")
                logger.info(f"[QUESTION ASSIGNMENT]    Question: {question_text}")
                
                return {
                    "success": True,
                    "message": f"Question assigned successfully. Question UUID: {question_uuid}",
                    "question_uuid": question_uuid
                }
                
            except Exception as db_error:
                # Handle potential unique constraint violation (race condition)
                # Another thread might have created the assignment between our check and create
                self.db.rollback()
                
                # Re-check if assignment was created by another thread
                existing_assignment = self.db.query(InterviewSystemDesign).filter(
                    InterviewSystemDesign.candidate_id == candidate_id
                ).first()
                
                if existing_assignment:
                    # Another thread created it - return existing (idempotent behavior)
                    logger.info(
                        f"[QUESTION ASSIGNMENT] ✅ Race condition detected - assignment created by another thread. "
                        f"Returning existing assignment for candidate {candidate_id}. Question UUID: {existing_assignment.question_uuid}"
                    )
                    return {
                        "success": True,
                        "message": f"Question already assigned. Question UUID: {existing_assignment.question_uuid}",
                        "question_uuid": existing_assignment.question_uuid
                    }
                else:
                    # Real database error - re-raise
                    raise db_error
                
        except Exception as e:
            self.db.rollback()
            error_msg = f"[QUESTION ASSIGNMENT] Unexpected error assigning question for candidate {candidate_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
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
            
            # Get question details (strip trailing spaces from UUID)
            question_uuid = assignment.question_uuid.strip() if assignment.question_uuid else None
            question = self.question_service.get_question_by_id(question_uuid)
            
            if not question:
                return None
            
            return {
                "candidate_id": candidate_id,
                "question_uuid": question_uuid,
                "question": question.question
            }
            
        except Exception as e:
            logger.error(f"Error fetching assigned question details for candidate {candidate_id}: {e}", exc_info=True)
            return None

