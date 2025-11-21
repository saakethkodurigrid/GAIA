"""
Question Assignment Service for managing system design question assignments to candidates.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from models.candidate import Candidate
from models.recruiter_admin_candidate import RecruiterAdminCandidate
from models.job import Job
from models.interview_system_design import InterviewSystemDesign
from utils.system_design.question_service import QuestionService


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
                return assignment.question_uuid
            return None
        except Exception as e:
            print(f"Error fetching assigned question: {e}")
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
                question = self.question_service.get_random_question_by_tag("normal_hld")
                return question.uuid if question else None
            
            # Get job details
            job = self.db.query(Job).filter(
                Job.job_id == assignment.job_id
            ).first()
            
            if not job:
                # Job not found, use default tag
                question = self.question_service.get_random_question_by_tag("normal_hld")
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
            
            # Get random question by tag
            question = self.question_service.get_random_question_by_tag(tag)
            
            if question:
                return question.uuid
            
            # If no question found with tag, try default
            question = self.question_service.get_random_question_by_tag("normal_hld")
            return question.uuid if question else None
            
        except Exception as e:
            print(f"Error selecting question by job role: {e}")
            # Fallback to default
            question = self.question_service.get_random_question_by_tag("normal_hld")
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
                question_uuid = self.select_question_by_job_role(candidate_id)
                
                if not question_uuid:
                    return {
                        "success": False,
                        "message": "Failed to auto-select question. No questions available."
                    }
            else:
                # Verify question exists
                question = self.question_service.get_question_by_id(question_uuid)
                if not question:
                    return {
                        "success": False,
                        "message": f"Question with UUID {question_uuid} not found"
                    }
            
            # Check if assignment already exists
            existing_assignment = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if existing_assignment:
                # Check if test has started (score is not NULL)
                if existing_assignment.score is not None:
                    return {
                        "success": False,
                        "message": "Cannot reassign question. Candidate has already completed the test."
                    }
                
                # Update existing assignment
                existing_assignment.question_uuid = question_uuid
                self.db.commit()
                
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
            
            import json
            tags_data = json.loads(question.tags) if isinstance(question.tags, str) else question.tags
            
            # Convert list to dictionary format if needed
            if isinstance(tags_data, list):
                tags_data = {tag: True for tag in tags_data}
            elif not isinstance(tags_data, dict):
                tags_data = None
            
            return {
                "candidate_id": candidate_id,
                "question_uuid": assignment.question_uuid,
                "question": question.question,
                "evaluation_criteria": question.evaluation_criteria,
                "tags": tags_data,
                "score": assignment.score,
                "diagram": assignment.diagram,
                "test_completed": assignment.score is not None
            }
            
        except Exception as e:
            print(f"Error fetching assigned question details: {e}")
            return None

