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
from schemas.mcq import MCQQuestionsResponse, MCQQuestionResponse, SaveMCQAnswerRequest, SaveMCQAnswerResponse, GenerateMCQRequest
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
                # Extract options from dedicated options column
                options = []
                if mcq.options and isinstance(mcq.options, list):
                    options = mcq.options
                # Fallback: check tags for backward compatibility (if old data exists)
                elif mcq.tags and isinstance(mcq.tags, dict):
                    if 'options' in mcq.tags and isinstance(mcq.tags['options'], list):
                        options = mcq.tags['options']
                
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
        Save or update candidate's answers for multiple MCQ questions and calculate scores.
        
        For each answer:
        - Compares candidate_answer with correct_answer
        - Sets score = 1 if correct, 0 if incorrect
        - Updates both candidate_answer and score in database
        
        Args:
            candidate_id: UUID of the candidate
            request: SaveMCQAnswerRequest with list of question-answer pairs
            
        Returns:
            SaveMCQAnswerResponse with success status, counts, and score information
        """
        saved_count = 0
        failed_count = 0
        failed_questions = []
        total_score = 0
        correct_answers = 0
        incorrect_answers = 0
        
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
                    
                    # Find which option number the candidate selected
                    # Candidate sends answer text, we need to match it to an option and get its index
                    candidate_answer_text = answer_item.candidate_answer.strip() if answer_item.candidate_answer else ""
                    candidate_option_number = None
                    
                    if mcq.options and isinstance(mcq.options, list):
                        # Match candidate's answer text to one of the options (case-insensitive)
                        for i, option_text in enumerate(mcq.options, 1):
                            if option_text and option_text.strip().lower() == candidate_answer_text.lower():
                                candidate_option_number = i
                                break
                    
                    # If no match found, mark as failed
                    if candidate_option_number is None:
                        failed_count += 1
                        failed_questions.append(answer_item.question_uuid)
                        continue
                    
                    # Store the option number (not the text)
                    mcq.candidate_answer = candidate_option_number
                    
                    # Calculate score: 1 if correct, 0 if incorrect
                    # Compare option numbers
                    if candidate_option_number == mcq.correct_answer:
                        mcq.score = 1
                        total_score += 1
                        correct_answers += 1
                    else:
                        mcq.score = 0
                        incorrect_answers += 1
                    
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
                message = f"Successfully saved {saved_count} answer(s). Score: {total_score}/{saved_count} ({correct_answers} correct, {incorrect_answers} incorrect)"
            elif saved_count == 0:
                message = f"Failed to save all {failed_count} answer(s)"
            else:
                message = f"Saved {saved_count} answer(s), {failed_count} failed. Score: {total_score}/{saved_count} ({correct_answers} correct, {incorrect_answers} incorrect)"
            
            return SaveMCQAnswerResponse(
                success=failed_count == 0,
                message=message,
                saved_count=saved_count,
                failed_count=failed_count,
                failed_questions=failed_questions,
                total_score=total_score,
                total_questions=saved_count,
                correct_answers=correct_answers,
                incorrect_answers=incorrect_answers
            )
            
        except Exception as e:
            # Rollback on critical error
            self.db.rollback()
            return SaveMCQAnswerResponse(
                success=False,
                message=f"Failed to save candidate answers. An unexpected error occurred: {str(e)}",
                saved_count=saved_count,
                failed_count=len(request.answers) - saved_count,
                failed_questions=[item.question_uuid for item in request.answers[saved_count:]],
                total_score=total_score,
                total_questions=saved_count,
                correct_answers=correct_answers,
                incorrect_answers=incorrect_answers
            )
    
    def save_test_schedule(self, candidate_id: str, request: ScheduleTestRequest) -> ScheduleTestResponse:
        """
        Save test schedule for a candidate and assign system design question and generate MCQ questions.
        
        This method:
        1. Updates the candidate's scheduled_date and status to 'scheduled'
        2. Calls QuestionAssignmentService to assign a system design question (parallel)
        3. Generates MCQ questions using RAG (parallel)
        
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
            
            # Validate that candidate is in 'shortlisted' status
            if candidate.status not in ['shortlisted', 'scheduled']:
                return ScheduleTestResponse(
                    success=False,
                    message=f"Cannot schedule test. Candidate status is '{candidate.status}'. Only 'shortlisted' or 'scheduled' candidates can schedule tests.",
                    scheduled_date=None
                )
            
            # Update candidate's scheduled_date and status
            candidate.scheduled_date = request.scheduled_date
            candidate.status = 'scheduled'
            
            # Commit the schedule update first
            self.db.commit()
            
            # Get job information for MCQ generation
            assignment = self.db.query(RecruiterAdminCandidate).filter(
                RecruiterAdminCandidate.candidate_id == candidate_id
            ).first()
            print("--------------------------------")
            if assignment:
                print(f"Assignment - recruiter_admin_email: {assignment.recruiter_admin_email}")
                print(f"Assignment - candidate_id: {assignment.candidate_id}")
                print(f"Assignment - job_id: {assignment.job_id}")
                print(f"Assignment - assigned_at: {assignment.assigned_at}")
                print(f"Assignment - job: {assignment.job}")
                print(f"Assignment - job_description: {assignment.job.job_description}")
                print(f"Assignment - job_role: {assignment.job.job_role}")

            else:
                print("Assignment: None")
                
            print(f"Candidate - candidate_id: {candidate.candidate_id}")
            print(f"Candidate - name: {candidate.name}")
            print(f"Candidate - email_id: {candidate.email_id}")
            print(f"Candidate - status: {candidate.status}")
            print(f"Candidate - scheduled_date: {candidate.scheduled_date}")
            print(f"Candidate - resume: {candidate.resume}")
            print("--------------------------------")
            # Parallel tasks: System Design Question Assignment and MCQ Generation
            system_design_result = None
            mcq_result = None
            error_messages = []
            
            # Task 1: Assign system design question to candidate
            try:
                from services.question_assignment_service import QuestionAssignmentService
                assignment_service = QuestionAssignmentService(self.db)
                system_design_result = assignment_service.assign_question_to_candidate(
                    candidate_id=candidate_id,
                    question_uuid=None  # Auto-select based on job role
                )
                if not system_design_result.get("success"):
                    error_messages.append(f"System design question assignment failed: {system_design_result.get('message', 'Unknown error')}")
            except Exception as e:
                error_messages.append(f"System design question assignment error: {str(e)}")
            
            # Task 2: Generate and save MCQ questions (if resume and job description are available)
            if candidate.resume and assignment and assignment.job:
                print("Inside if condition..............")
                try:
                    print("Inside try block..............")
                    try:
                        from services.mcq_generation_service import MCQGenerationService
                        try:
                            mcq_service = MCQGenerationService(self.db)
                        except Exception as e:
                            print(f"MCQ service initialization error: {str(e)}")
                        print("MCQ service initialized..............")
                    except Exception as e:
                        print(f"MCQ service initialization error: {str(e)}")
                    # if candidate.resume is None and assignment.job is None:
                    #     from services.sample_data_for_mcq import job_description, resume
                    #     mcq_request = GenerateMCQRequest(
                    #         resume=resume,
                    #         job_description=job_description,
                    #         grade="T2"  # Default to T2, can be made configurable later
                    #     )
                    # else:
                        # Create request for MCQ generation
                    print("Generating MCQ questions..............")
                    print(f"Candidate - resume: {candidate.resume}")
                    print(f"Assignment - job_description: {assignment.job.job_description}")
                    print(f"Assignment - job_role: {assignment.job.job_role}")
                    print(f"Assignment - job_grade: {assignment.job.grade}")
                    print("--------------------------------")
                    # Get grade from job, validate it's T2 or T3 for MCQ generation, default to T2 if invalid
                    job_grade = assignment.job.grade if assignment.job.grade in ["T2", "T3"] else "T2"
                    mcq_request = GenerateMCQRequest(
                        resume=candidate.resume,
                        job_description=assignment.job.job_description,
                        grade=job_grade
                    )
                    print(f"MCQ request: {mcq_request}")
                    # Generate questions
                    generation_result = mcq_service.generate_questions(mcq_request)
                    questions = generation_result.get("questions", [])
                    
                    if questions:
                        # Save generated questions to database
                        save_result = mcq_service.save_generated_questions(
                            candidate_id=candidate_id,
                            questions=questions
                        )
                        if save_result.get("success"):
                            mcq_result = {
                                "success": True,
                                "message": f"Generated and saved {save_result.get('saved_count', 0)} MCQ questions"
                            }
                        else:
                            error_messages.append(f"MCQ generation succeeded but saving failed: {save_result.get('message', 'Unknown error')}")
                    else:
                        error_messages.append("MCQ generation returned no questions")
                        
                except Exception as e:
                    error_messages.append(f"MCQ generation error: {str(e)}")
            else:
                if not candidate.resume:
                    error_messages.append("MCQ generation skipped: Candidate resume not available")
                elif not assignment or not assignment.job:
                    error_messages.append("MCQ generation skipped: Job assignment or job description not available")
            
            # Build response message
            base_message = f"Test scheduled successfully for {request.scheduled_date.isoformat()}"
            if error_messages:
                base_message += f". Warnings: {'; '.join(error_messages)}"
            
            return ScheduleTestResponse(
                success=True,
                message=base_message,
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

