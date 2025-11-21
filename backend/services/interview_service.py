"""
Interview service for managing interviews.
"""
from datetime import datetime, date
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from models.candidate import Candidate
from models.recruiter_admin_candidate import RecruiterAdminCandidate
from models.job import Job
from models.interview_mcq import InterviewMCQ
from schemas.admin import ListInterviewsResponse, InterviewResponse
from schemas.mcq import MCQQuestionsResponse, MCQQuestionResponse, SaveMCQAnswerRequest, SaveMCQAnswerResponse
from schemas.candidate import ScheduleTestRequest, ScheduleTestResponse


class InterviewService:
    """Interview service class for managing interviews."""
    
    def __init__(self, db: Session):
        """Initialize interview service with database session."""
        self.db = db
    
    def list_today_interviews(self, user_email: str, user_role_id: int) -> ListInterviewsResponse:
        """
        List interviews scheduled for today based on user role.
        
        - Recruiters (role_id = 1): Only see interviews for candidates assigned to them
        - Admins (role_id = 2): See all interviews scheduled for today
        
        Args:
            user_email: Email of the current user
            user_role_id: Role ID of the current user (1 = Recruiter, 2 = Admin)
            
        Returns:
            ListInterviewsResponse with list of interviews
        """
        try:
            # Get today's date
            today = date.today()
            
            # Base query: candidates with scheduled_date today
            # Use func.date() to extract date part from DateTime for comparison
            base_query = self.db.query(
                Candidate,
                RecruiterAdminCandidate,
                Job
            ).join(
                RecruiterAdminCandidate,
                Candidate.candidate_id == RecruiterAdminCandidate.candidate_id
            ).join(
                Job,
                RecruiterAdminCandidate.job_id == Job.job_id
            ).filter(
                and_(
                    func.date(Candidate.scheduled_date) == today,
                    Candidate.scheduled_date.isnot(None)
                )
            )
            
            # If user is recruiter, filter by their email
            if user_role_id == 1:
                base_query = base_query.filter(
                    RecruiterAdminCandidate.recruiter_admin_email == user_email.lower()
                )
            # If user is admin, get all interviews (no additional filter)
            elif user_role_id != 2:
                return ListInterviewsResponse(
                    success=False,
                    message="Invalid user role. Only recruiters and admins can list interviews.",
                    count=0,
                    interviews=[]
                )
            
            # Execute query
            results = base_query.all()
            
            # Convert to response format
            interview_list = []
            for candidate, assignment, job in results:
                # scheduled_date should not be None since we filter for it, but handle it just in case
                scheduled_date_str = candidate.scheduled_date.isoformat() if candidate.scheduled_date else ""
                interview_list.append(
                    InterviewResponse(
                        candidate_id=candidate.candidate_id,
                        candidate_name=candidate.name,
                        candidate_email=candidate.email_id,
                        job_id=job.job_id,
                        job_role=job.job_role,
                        recruiter_email=assignment.recruiter_admin_email,
                        scheduled_date=scheduled_date_str,
                        status=candidate.status
                    )
                )
            
            return ListInterviewsResponse(
                success=True,
                message=f"Successfully retrieved {len(interview_list)} interview(s) scheduled for today",
                count=len(interview_list),
                interviews=interview_list
            )
            
        except Exception as e:
            return ListInterviewsResponse(
                success=False,
                message=f"Failed to retrieve interviews. An unexpected error occurred: {str(e)}",
                count=0,
                interviews=[]
            )
    
    def list_interviews(
        self,
        user_email: str,
        user_role_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> ListInterviewsResponse:
        """
        List interviews with optional date filtering.
        
        Handles three scenarios:
        1. Date range: Both start_date and end_date provided
        2. Single date: Only start_date provided (end_date is None)
        3. Today: If no dates provided, defaults to today
        
        Args:
            user_email: Email of the current user
            user_role_id: Role ID (1 = Recruiter, 2 = Admin)
            start_date: Start date for filtering (optional)
            end_date: End date for filtering (optional, only used if start_date is provided)
        
        Returns:
            ListInterviewsResponse with filtered interviews
        """
        try:
            # Determine date range
            if start_date is None:
                # No dates provided - default to today
                filter_start = date.today()
                filter_end = date.today()
            elif end_date is None:
                # Only start_date provided - single date filter
                filter_start = start_date
                filter_end = start_date
            else:
                # Both dates provided - date range filter
                filter_start = start_date
                filter_end = end_date
            
            # Validate date range
            if filter_start > filter_end:
                return ListInterviewsResponse(
                    success=False,
                    message="Start date cannot be after end date.",
                    count=0,
                    interviews=[]
                )
            
            # Base query: candidates with scheduled_date in range
            base_query = self.db.query(
                Candidate,
                RecruiterAdminCandidate,
                Job
            ).join(
                RecruiterAdminCandidate,
                Candidate.candidate_id == RecruiterAdminCandidate.candidate_id
            ).join(
                Job,
                RecruiterAdminCandidate.job_id == Job.job_id
            ).filter(
                and_(
                    func.date(Candidate.scheduled_date) >= filter_start,
                    func.date(Candidate.scheduled_date) <= filter_end,
                    Candidate.scheduled_date.isnot(None)
                )
            )
            
            # If user is recruiter, filter by their email
            if user_role_id == 1:
                base_query = base_query.filter(
                    RecruiterAdminCandidate.recruiter_admin_email == user_email.lower()
                )
            # If user is admin, get all interviews (no additional filter)
            elif user_role_id != 2:
                return ListInterviewsResponse(
                    success=False,
                    message="Invalid user role. Only recruiters and admins can list interviews.",
                    count=0,
                    interviews=[]
                )
            
            # Execute query
            results = base_query.all()
            
            # Convert to response format
            interview_list = []
            for candidate, assignment, job in results:
                scheduled_date_str = candidate.scheduled_date.isoformat() if candidate.scheduled_date else ""
                interview_list.append(
                    InterviewResponse(
                        candidate_id=candidate.candidate_id,
                        candidate_name=candidate.name,
                        candidate_email=candidate.email_id,
                        job_id=job.job_id,
                        job_role=job.job_role,
                        recruiter_email=assignment.recruiter_admin_email,
                        scheduled_date=scheduled_date_str,
                        status=candidate.status
                    )
                )
            
            # Build message based on filter type
            if start_date is None:
                message = f"Successfully retrieved {len(interview_list)} interview(s) scheduled for today"
            elif end_date is None:
                message = f"Successfully retrieved {len(interview_list)} interview(s) scheduled for {start_date}"
            else:
                message = f"Successfully retrieved {len(interview_list)} interview(s) scheduled from {start_date} to {end_date}"
            
            return ListInterviewsResponse(
                success=True,
                message=message,
                count=len(interview_list),
                interviews=interview_list
            )
            
        except Exception as e:
            return ListInterviewsResponse(
                success=False,
                message=f"Failed to retrieve interviews. An unexpected error occurred: {str(e)}",
                count=0,
                interviews=[]
            )
    
    def get_mcq_questions(self, candidate_id: str) -> MCQQuestionsResponse:
        """
        Get all MCQ questions and options for a candidate.
        
        Only returns question text and options, no other information from the table.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            MCQQuestionsResponse with list of questions and their options
        """
        try:
            # Fetch all MCQ questions for the candidate
            mcq_records = self.db.query(InterviewMCQ).filter(
                InterviewMCQ.candidate_id == candidate_id
            ).all()
            
            if not mcq_records:
                return MCQQuestionsResponse(
                    success=True,
                    message="No MCQ questions found for this candidate",
                    count=0,
                    questions=[]
                )
            
            # Convert to response format
            questions_list = []
            for mcq in mcq_records:
                # Extract options from tags if available, otherwise empty list
                # Assuming options might be stored in tags as a JSON array
                options = []
                if mcq.tags and isinstance(mcq.tags, dict):
                    # Check if options are in tags
                    if 'options' in mcq.tags and isinstance(mcq.tags['options'], list):
                        options = mcq.tags['options']
                    elif isinstance(mcq.tags, list):
                        # If tags is a list, it might be the options
                        options = mcq.tags
                
                questions_list.append(
                    MCQQuestionResponse(
                        question_uuid=mcq.uuid,
                        question=mcq.question,
                        options=options
                    )
                )
            
            return MCQQuestionsResponse(
                success=True,
                message=f"Successfully retrieved {len(questions_list)} MCQ question(s)",
                count=len(questions_list),
                questions=questions_list
            )
            
        except Exception as e:
            return MCQQuestionsResponse(
                success=False,
                message=f"Failed to retrieve MCQ questions. An unexpected error occurred: {str(e)}",
                count=0,
                questions=[]
            )
    
    def save_mcq_answers(self, candidate_id: str, request: SaveMCQAnswerRequest) -> SaveMCQAnswerResponse:
        """
        Save or update candidate's answers for multiple MCQ questions.
        
        Args:
            candidate_id: UUID of the candidate
            request: SaveMCQAnswerRequest with list of question-answer pairs
            
        Returns:
            SaveMCQAnswerResponse with success status and counts
        """
        saved_count = 0
        failed_count = 0
        failed_questions = []
        
        try:
            # Process each answer in the list
            for answer_item in request.answers:
                try:
                    # Find the MCQ question for this candidate
                    mcq = self.db.query(InterviewMCQ).filter(
                        InterviewMCQ.uuid == answer_item.question_uuid,
                        InterviewMCQ.candidate_id == candidate_id
                    ).first()
                    
                    if not mcq:
                        failed_count += 1
                        failed_questions.append(answer_item.question_uuid)
                        continue
                    
                    # Update the candidate answer
                    mcq.candidate_answer = answer_item.candidate_answer
                    saved_count += 1
                    
                except Exception as e:
                    # Log error for this specific question but continue with others
                    failed_count += 1
                    failed_questions.append(answer_item.question_uuid)
                    continue
            
            # Commit all changes at once
            self.db.commit()
            
            # Build response message
            if failed_count == 0:
                message = f"Successfully saved {saved_count} answer(s)"
            elif saved_count == 0:
                message = f"Failed to save all {failed_count} answer(s)"
            else:
                message = f"Saved {saved_count} answer(s), {failed_count} failed"
            
            return SaveMCQAnswerResponse(
                success=failed_count == 0,
                message=message,
                saved_count=saved_count,
                failed_count=failed_count,
                failed_questions=failed_questions
            )
            
        except Exception as e:
            # Rollback on critical error
            self.db.rollback()
            return SaveMCQAnswerResponse(
                success=False,
                message=f"Failed to save candidate answers. An unexpected error occurred: {str(e)}",
                saved_count=saved_count,
                failed_count=len(request.answers) - saved_count,
                failed_questions=[item.question_uuid for item in request.answers[saved_count:]]
            )
    
    def save_test_schedule(self, candidate_id: str, request: ScheduleTestRequest) -> ScheduleTestResponse:
        """
        Save test schedule for a candidate and assign system design question.
        
        This method:
        1. Updates the candidate's scheduled_date and status to 'scheduled'
        2. Calls QuestionAssignmentService to assign a system design question
        
        Args:
            candidate_id: UUID of the candidate
            request: ScheduleTestRequest with scheduled_date
            
        Returns:
            ScheduleTestResponse with success status and scheduled_date
        """
        try:
            # Verify candidate exists
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                return ScheduleTestResponse(
                    success=False,
                    message=f"Candidate with ID {candidate_id} not found",
                    scheduled_date=None
                )
            
            # Validate that candidate is in 'registered' status
            if candidate.status not in ['registered', 'scheduled']:
                return ScheduleTestResponse(
                    success=False,
                    message=f"Cannot schedule test. Candidate status is '{candidate.status}'. Only 'registered' or 'scheduled' candidates can schedule tests.",
                    scheduled_date=None
                )
            
            # Update candidate's scheduled_date and status
            candidate.scheduled_date = request.scheduled_date
            candidate.status = 'scheduled'
            
            # Commit the schedule update first
            self.db.commit()
            
            # Assign system design question to candidate
            from services.question_assignment_service import QuestionAssignmentService
            assignment_service = QuestionAssignmentService(self.db)
            assignment_result = assignment_service.assign_question_to_candidate(
                candidate_id=candidate_id,
                question_uuid=None  # Auto-select based on job role
            )
            
            # Check if question assignment was successful
            if not assignment_result.get("success"):
                # Schedule was saved but question assignment failed
                return ScheduleTestResponse(
                    success=True,
                    message=f"Test scheduled successfully for {request.scheduled_date.isoformat()}, but failed to assign system design question: {assignment_result.get('message', 'Unknown error')}",
                    scheduled_date=request.scheduled_date.isoformat()
                )
            
            return ScheduleTestResponse(
                success=True,
                message=f"Test scheduled successfully for {request.scheduled_date.isoformat()}",
                scheduled_date=request.scheduled_date.isoformat()
            )
            
        except Exception as e:
            # Rollback on error
            self.db.rollback()
            return ScheduleTestResponse(
                success=False,
                message=f"Failed to save test schedule. An unexpected error occurred: {str(e)}",
                scheduled_date=None
            )

