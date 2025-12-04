"""
Test Session service for managing test sessions and tab closure auto-completion.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from models.test_session import TestSession
from models.candidate import Candidate
from models.interview_mcq import InterviewMCQ
from schemas.test_session import (
    StartTestResponse,
    CompleteTestResponse,
    TestStatusResponse,
    HeartbeatResponse,
    CompleteTestRequest
)
from schemas.mcq import SaveMCQAnswerRequest

logger = logging.getLogger(__name__)


class TestSessionService:
    """Service for managing test sessions."""
    
    def __init__(self, db: Session):
        """Initialize test session service with database session."""
        self.db = db
    
    def create_test_session(self, candidate_id: str, duration_minutes: int = 60) -> StartTestResponse:
        """
        Create a new test session for a candidate.
        
        Args:
            candidate_id: UUID of the candidate
            duration_minutes: Test duration in minutes (default: 60)
            
        Returns:
            StartTestResponse with session details
        """
        try:
            # Check if candidate exists
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                return StartTestResponse(
                    success=False,
                    message="Candidate not found",
                    test_start_time=None,
                    remaining_seconds=0
                )
            
            # Check if session already exists
            existing_session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id
            ).first()
            
            if existing_session:
                # Update existing session if it's not completed
                if existing_session.status == 'active':
                    # Calculate remaining time
                    elapsed = datetime.utcnow() - existing_session.test_start_time
                    remaining = timedelta(minutes=duration_minutes) - elapsed
                    remaining_seconds = max(0, int(remaining.total_seconds()))
                    
                    return StartTestResponse(
                        success=True,
                        message="Test session already exists",
                        test_start_time=existing_session.test_start_time,
                        remaining_seconds=remaining_seconds
                    )
                else:
                    # Create new session if previous one is completed
                    existing_session.test_start_time = datetime.utcnow()
                    existing_session.test_duration_minutes = duration_minutes
                    existing_session.status = 'active'
                    existing_session.last_heartbeat = datetime.utcnow()
                    existing_session.last_activity = datetime.utcnow()
                    existing_session.completion_method = None
                    existing_session.completed_at = None
                    existing_session.sections_completed = None
                    existing_session.pending_answers = None
            else:
                # Create new session
                test_start_time = datetime.utcnow()
                new_session = TestSession(
                    candidate_id=candidate_id,
                    test_start_time=test_start_time,
                    test_duration_minutes=duration_minutes,
                    status='active',
                    last_heartbeat=datetime.utcnow(),
                    last_activity=datetime.utcnow(),
                    sections_completed={},
                    pending_answers={}
                )
                self.db.add(new_session)
            
            # Update candidate status to 'in progress' if not already
            if candidate.status != 'in progress':
                candidate.status = 'in progress'
            
            self.db.commit()
            
            # Calculate remaining time
            session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id
            ).first()
            
            elapsed = datetime.utcnow() - session.test_start_time
            remaining = timedelta(minutes=duration_minutes) - elapsed
            remaining_seconds = max(0, int(remaining.total_seconds()))
            
            return StartTestResponse(
                success=True,
                message="Test session created successfully",
                test_start_time=session.test_start_time,
                remaining_seconds=remaining_seconds
            )
            
        except IntegrityError as e:
            self.db.rollback()
            logger.error(f"Error creating test session: {str(e)}")
            return StartTestResponse(
                success=False,
                message=f"Failed to create test session: {str(e)}",
                test_start_time=None,
                remaining_seconds=0
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Unexpected error creating test session: {str(e)}")
            return StartTestResponse(
                success=False,
                message=f"An unexpected error occurred: {str(e)}",
                test_start_time=None,
                remaining_seconds=0
            )
    
    def update_heartbeat(self, candidate_id: str) -> HeartbeatResponse:
        """
        Update heartbeat timestamp for a test session.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            HeartbeatResponse with server timestamp
        """
        try:
            session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id,
                TestSession.status == 'active'
            ).first()
            
            if not session:
                return HeartbeatResponse(
                    success=False,
                    message="No active test session found",
                    server_timestamp=datetime.utcnow(),
                    remaining_seconds=0
                )
            
            now = datetime.utcnow()
            session.last_heartbeat = now
            session.last_activity = now
            
            self.db.commit()
            
            # Calculate remaining time
            elapsed = now - session.test_start_time
            remaining = timedelta(minutes=session.test_duration_minutes) - elapsed
            remaining_seconds = max(0, int(remaining.total_seconds()))
            
            return HeartbeatResponse(
                success=True,
                message="Heartbeat updated",
                server_timestamp=now,
                remaining_seconds=remaining_seconds
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating heartbeat: {str(e)}")
            return HeartbeatResponse(
                success=False,
                message=f"Error updating heartbeat: {str(e)}",
                server_timestamp=datetime.utcnow(),
                remaining_seconds=0
            )
    
    def update_last_activity(self, candidate_id: str) -> bool:
        """
        Update last activity timestamp (more frequent than heartbeat).
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            True if updated, False otherwise
        """
        try:
            session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id,
                TestSession.status == 'active'
            ).first()
            
            if session:
                session.last_activity = datetime.utcnow()
                self.db.commit()
                return True
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating last activity: {str(e)}")
            return False
    
    def save_pending_answers(self, candidate_id: str, answers_data: Dict[str, Any]) -> bool:
        """
        Save pending answers temporarily (for tab close recovery).
        
        Args:
            candidate_id: UUID of the candidate
            answers_data: Dictionary with pending answers for each section
            
        Returns:
            True if saved, False otherwise
        """
        try:
            session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id,
                TestSession.status == 'active'
            ).first()
            
            if session:
                session.pending_answers = answers_data
                session.last_activity = datetime.utcnow()
                self.db.commit()
                return True
            return False
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving pending answers: {str(e)}")
            return False
    
    def complete_test_session(
        self,
        candidate_id: str,
        completion_method: str,
        request: CompleteTestRequest
    ) -> CompleteTestResponse:
        """
        Complete a test session and save all answers.
        
        Args:
            candidate_id: UUID of the candidate
            completion_method: How test was completed ('manual', 'tab_close', 'timer_expired', etc.)
            request: CompleteTestRequest with all answers
            
        Returns:
            CompleteTestResponse with completion confirmation
        """
        try:
            # Get test session
            session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id
            ).first()
            
            if not session:
                return CompleteTestResponse(
                    success=False,
                    message="Test session not found",
                    completed_at=None
                )
            
            # Check if already completed
            if session.status == 'completed':
                return CompleteTestResponse(
                    success=True,
                    message="Test already completed",
                    completed_at=session.completed_at
                )
            
            # Save MCQ answers if provided
            if request.mcq_answers and request.mcq_answers.answers:
                # Lazy import to avoid circular dependency
                from services.interview_service import InterviewService
                interview_service = InterviewService(self.db)
                mcq_response = interview_service.save_mcq_answers(candidate_id, request.mcq_answers)
                if not mcq_response.success:
                    logger.warning(f"Some MCQ answers failed to save: {mcq_response.message}")
            
            # TODO: Save coding answers if provided
            # TODO: Save system design answers if provided
            
            # Update test session
            now = datetime.utcnow()
            session.status = 'completed'
            session.completion_method = completion_method
            session.completed_at = now
            session.sections_completed = request.sections_completed or {}
            session.pending_answers = None  # Clear pending answers after completion
            
            # Update candidate status
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            if candidate:
                candidate.status = 'completed'
            
            self.db.commit()
            
            return CompleteTestResponse(
                success=True,
                message="Test completed successfully",
                completed_at=now
            )
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error completing test session: {str(e)}")
            return CompleteTestResponse(
                success=False,
                message=f"Failed to complete test: {str(e)}",
                completed_at=None
            )
    
    def get_test_session(self, candidate_id: str) -> Optional[TestSession]:
        """
        Get test session for a candidate.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            TestSession object or None
        """
        return self.db.query(TestSession).filter(
            TestSession.candidate_id == candidate_id
        ).first()
    
    def get_remaining_time(self, candidate_id: str) -> int:
        """
        Calculate remaining time for a test session.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Remaining seconds (0 if expired or not found)
        """
        session = self.get_test_session(candidate_id)
        if not session or session.status != 'active':
            return 0
        
        elapsed = datetime.utcnow() - session.test_start_time
        remaining = timedelta(minutes=session.test_duration_minutes) - elapsed
        return max(0, int(remaining.total_seconds()))
    
    def get_test_status(self, candidate_id: str) -> TestStatusResponse:
        """
        Get current test status for a candidate.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            TestStatusResponse with current status
        """
        session = self.get_test_session(candidate_id)
        
        if not session:
            return TestStatusResponse(
                success=False,
                message="No test session found",
                status=None,
                remaining_seconds=0,
                sections_completed={},
                last_activity=None
            )
        
        remaining_seconds = self.get_remaining_time(candidate_id)
        
        return TestStatusResponse(
            success=True,
            message="Test session found",
            status=session.status,
            remaining_seconds=remaining_seconds,
            sections_completed=session.sections_completed or {},
            last_activity=session.last_activity
        )

