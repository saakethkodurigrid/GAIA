"""
Interview service for managing interviews.
"""
import logging
import asyncio
import random
import threading
import json
from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from models.candidate import Candidate
from models.recruiter_admin_candidate import RecruiterAdminCandidate
from models.job import Job
from models.interview_mcq import InterviewMCQ
from models.interview_coding import InterviewCoding
from models.coding_question_bank import CodingQuestionBank
from models.interview_analysis_table import InterviewAnalysisTable
from models.test_session import TestSession
from models.interview_system_design import InterviewSystemDesign
from schemas.admin import ListInterviewsResponse, InterviewResponse
from schemas.mcq import (
    MCQQuestionsResponse, MCQQuestionResponse, SaveMCQAnswerRequest, 
    SaveMCQAnswerResponse, GenerateMCQRequest, AutosaveMCQAnswerResponse,
    SubmitMCQAnswerResponse, MCQAnswerItem
)
from schemas.candidate import ScheduleTestRequest, ScheduleTestResponse
from services.email_service import email_service
from services.question_assignment_service import QuestionAssignmentService
from services.coding_question_assignment_service import CodingQuestionAssignmentService
from core.redis_client import get_redis_client
from core.config import settings
from utils.mcq_redis_helper import save_mcq_draft, get_mcq_draft, clear_mcq_draft
from utils.analysis_summary import generate_interview_summary

logger = logging.getLogger(__name__)


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
                        candidate_id=candidate.candidate_reference_number,  # Return reference number only
                        candidate_name=candidate.name,
                        candidate_email=candidate.email_id,
                        job_id=job.job_reference_number or job.job_id,  # Return reference number, fallback to UUID if None
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
                        candidate_id=candidate.candidate_reference_number,  # Return reference number only
                        candidate_name=candidate.name,
                        candidate_email=candidate.email_id,
                        job_id=job.job_reference_number or job.job_id,  # Return reference number, fallback to UUID if None
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
             # Fetch only the columns we need: uuid, question, and options
            mcq_records = self.db.query(
                InterviewMCQ.uuid,
                InterviewMCQ.question,
                InterviewMCQ.options
            ).filter(
                InterviewMCQ.candidate_id == candidate_id
            ).all()
            
            if not mcq_records:
                return MCQQuestionsResponse(
                    success=True,
                    message="No MCQ questions found for this candidate",
                    count=0,
                    questions=[]
                )
            
            # Convert to response format using list comprehension
            questions_list = [
                MCQQuestionResponse(
                    question_uuid=mcq.uuid,
                    question=mcq.question,
                    options=mcq.options or []
                )
                for mcq in mcq_records
            ]

            # Shuffle the questions to randomize their order
            random.shuffle(questions_list)
            
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
        Save candidate's MCQ answers - submission-only method (legacy wrapper).
        
        This method is kept for backward compatibility with complete_test endpoint.
        It delegates to submit_mcq_answers() which handles final submission.
        
        This method:
        - Does NOT write to Redis (submission-only)
        - Persists to PostgreSQL
        - Calculates scores
        - Marks assessment as submitted
        - Is idempotent (safe to call multiple times)
        
        Args:
            candidate_id: UUID of the candidate
            request: SaveMCQAnswerRequest with list of question-answer pairs
            
        Returns:
            SaveMCQAnswerResponse with success status, counts, and score information
        """
        # Delegate to submit_mcq_answers for final submission
        submit_response = self.submit_mcq_answers(candidate_id, request)
        
        # Convert SubmitMCQAnswerResponse to SaveMCQAnswerResponse for backward compatibility
        return SaveMCQAnswerResponse(
            success=submit_response.success,
            message=submit_response.message,
            saved_count=submit_response.saved_count,
            failed_count=submit_response.failed_count,
            failed_questions=submit_response.failed_questions,
            total_score=submit_response.total_score,
            total_questions=submit_response.total_questions,
            correct_answers=submit_response.correct_answers,
            incorrect_answers=submit_response.incorrect_answers
        )
    
    def _update_mcq_analysis(self, candidate_id: str) -> None:
        """
        Calculate and update MCQ analysis in interview_analysis_table.
        
        Delegates to standalone analyze_mcq function for background-safe execution.
        
        Args:
            candidate_id: UUID of the candidate
        """
        from services.section_analysis_service import analyze_mcq
        analyze_mcq(candidate_id, self.db)
    
    def autosave_mcq_answers(self, candidate_id: str, request: SaveMCQAnswerRequest) -> AutosaveMCQAnswerResponse:
        """
        Autosave candidate's MCQ answers to Redis only (draft storage).
        
        This method is a best-effort, silent draft mechanism that never blocks or errors
        from the frontend's perspective. It:
        - Checks if MCQ is already submitted (no-op if submitted)
        - Saves answers to Redis with TTL using Redis helper
        - Does NOT write to PostgreSQL
        - Does NOT calculate scores
        - Does NOT update candidate status or test_session
        - Does NOT track activity
        - Always returns success=True (fire-and-forget)
        
        Authentication is guaranteed by the route handler, so no candidate validation needed.
        
        Args:
            candidate_id: UUID of the candidate (authenticated via route)
            request: SaveMCQAnswerRequest with list of question-answer pairs
            
        Returns:
            AutosaveMCQAnswerResponse with success=True always, saved_count=0 if no-op or failure
        """
        timestamp = datetime.utcnow().isoformat()
        
        try:
            # Check if MCQ section is already submitted (authoritative signal)
            # If submitted, return successful no-op to prevent overwriting drafts
            test_session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id
            ).first()
            
            if test_session and test_session.sections_completed:
                sections_completed = test_session.sections_completed
                if isinstance(sections_completed, dict) and sections_completed.get("mcq") is True:
                    logger.info(f"Autosave no-op: MCQ section already submitted for candidate {candidate_id}")
                    return AutosaveMCQAnswerResponse(
                        success=True,
                        message="MCQ section already submitted. Autosave skipped.",
                        saved_count=0,
                        last_updated_at=timestamp
                    )
            
            # Convert to format expected by Redis helper
            answers_list = [
                {
                    "question_uuid": item.question_uuid,
                    "candidate_answer": item.candidate_answer
                }
                for item in request.answers
            ]
            
            # Save to Redis using helper (best-effort)
            success = save_mcq_draft(candidate_id, answers_list)
            
            if success:
                logger.info(f"Autosave to Redis successful for candidate {candidate_id}: {len(request.answers)} answers")
                return AutosaveMCQAnswerResponse(
                    success=True,
                    message=f"Successfully autosaved {len(request.answers)} answer(s) to Redis",
                    saved_count=len(request.answers),
                    last_updated_at=timestamp
                )
            else:
                # Redis failure - return success=True (fire-and-forget, never surface as failure)
                logger.warning(f"Redis autosave failed for candidate {candidate_id}, but returning success (fire-and-forget)")
                return AutosaveMCQAnswerResponse(
                    success=True,
                    message="Autosave initiated (Redis unavailable)",
                    saved_count=0,
                    last_updated_at=timestamp
                )
                
        except Exception as e:
            # Any exception - return success=True (fire-and-forget, never surface as failure)
            logger.warning(f"Error in autosave_mcq_answers for candidate {candidate_id}: {str(e)}, but returning success (fire-and-forget)", exc_info=True)
            return AutosaveMCQAnswerResponse(
                success=True,
                message="Autosave initiated",
                saved_count=0,
                last_updated_at=timestamp
            )
    
    def submit_mcq_answers(self, candidate_id: str, request: SaveMCQAnswerRequest) -> SubmitMCQAnswerResponse:
        """
        Final submission of candidate's MCQ answers to PostgreSQL.
        
        This method:
        - Validates candidate is allowed to submit
        - Checks idempotency (returns existing results if already submitted)
        - Fetches latest draft from Redis (if exists)
        - Merges Redis answers with request payload (request takes precedence)
        - Persists final answers to PostgreSQL (if any)
        - Marks assessment as submitted in test_session (even with zero answers)
        - Triggers scoring and analysis (handles zero answers correctly)
        - Clears Redis draft after successful save (always, even for zero-answer submission)
        - Supports zero-answer submission as a valid state transition
        
        Idempotency: If test_session.sections_completed["mcq"] == True, immediately returns
        existing results without re-scoring or re-writing data.
        
        Zero-answer submission: When final_answers is empty:
        - Does NOT save any InterviewMCQ rows
        - Does NOT calculate scores
        - Still marks MCQ section as submitted
        - Still clears Redis draft
        - Returns success=True with all counts/scores as 0
        
        Args:
            candidate_id: UUID of the candidate
            request: SaveMCQAnswerRequest with list of question-answer pairs (can be empty)
            
        Returns:
            SubmitMCQAnswerResponse with success status, counts, and score information
        """
        saved_count = 0
        failed_count = 0
        failed_questions = []
        total_score = 0
        correct_answers = 0
        incorrect_answers = 0
        
        # Define difficulty scoring weights
        DIFFICULTY_SCORES = {
            "hard": 3,
            "medium": 2,
            "easy": 1
        }
        
        try:
            # Validate candidate exists
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if not candidate:
                return SubmitMCQAnswerResponse(
                    success=False,
                    message=f"Candidate {candidate_id} not found",
                    saved_count=0,
                    failed_count=len(request.answers),
                    failed_questions=[item.question_uuid for item in request.answers],
                    total_score=0,
                    total_questions=0,
                    correct_answers=0,
                    incorrect_answers=0,
                    submitted_at=datetime.utcnow().isoformat()
                )
            
            # Get total number of MCQ questions assigned to this candidate
            total_questions_assigned = self.db.query(InterviewMCQ).filter(
                InterviewMCQ.candidate_id == candidate_id
            ).count()
            
            # Check if already submitted (idempotency check)
            test_session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id
            ).first()
            
            if test_session and test_session.sections_completed:
                sections_completed = test_session.sections_completed
                if isinstance(sections_completed, dict) and sections_completed.get("mcq") is True:
                    logger.info(f"MCQ section already submitted for candidate {candidate_id}, returning existing results")
                    
                    # Return existing results without re-processing (idempotent)
                    all_mcqs = self.db.query(InterviewMCQ).filter(
                        InterviewMCQ.candidate_id == candidate_id
                    ).all()
                    
                    for mcq in all_mcqs:
                        if mcq.candidate_answer is not None:
                            saved_count += 1
                            difficulty = mcq.difficulty.lower()
                            difficulty_score = DIFFICULTY_SCORES.get(difficulty)
                            if mcq.candidate_answer == mcq.correct_answer:
                                total_score += difficulty_score
                                correct_answers += 1
                            else:
                                incorrect_answers += 1
                    
                    return SubmitMCQAnswerResponse(
                        success=True,
                        message="MCQ section already submitted. Returning existing results.",
                        saved_count=saved_count,
                        failed_count=0,
                        failed_questions=[],
                        total_score=total_score,
                        total_questions=total_questions_assigned,
                        correct_answers=correct_answers,
                        incorrect_answers=incorrect_answers,
                        submitted_at=test_session.sections_completed.get("mcq_submitted_at", datetime.utcnow().isoformat())
                    )
            
            # Fetch draft from Redis and merge with request
            merged_answers = {}
            
            # First, add all answers from request (these take precedence)
            for item in request.answers:
                merged_answers[item.question_uuid] = item.candidate_answer
            
            # Then, fetch from Redis and fill in any missing answers
            redis_draft = get_mcq_draft(candidate_id)
            if redis_draft:
                for answer_item in redis_draft:
                    question_uuid = answer_item.get("question_uuid")
                    candidate_answer = answer_item.get("candidate_answer")
                    # Only add if not already in merged_answers (request takes precedence)
                    if question_uuid and candidate_answer and question_uuid not in merged_answers:
                        merged_answers[question_uuid] = candidate_answer
                logger.info(f"Merged {len(redis_draft)} answers from Redis for candidate {candidate_id}")
            
            # Convert merged answers to list format for processing
            final_answers = [
                MCQAnswerItem(
                    question_uuid=q_uuid,
                    candidate_answer=answer
                )
                for q_uuid, answer in merged_answers.items()
            ]
            
            # Process answers if any exist (zero-answer submission is valid)
            if final_answers:
                # Collect all question UUIDs for batch fetch (eliminate N+1 queries)
                question_uuids = [item.question_uuid for item in final_answers]
                
                # Single SELECT query: fetch all matching InterviewMCQ rows at once
                mcq_rows = self.db.query(InterviewMCQ).filter(
                    InterviewMCQ.candidate_id == candidate_id,
                    InterviewMCQ.uuid.in_(question_uuids)
                ).all()
                
                # Build in-memory map for O(1) lookup: {uuid -> InterviewMCQ}
                mcq_map = {mcq.uuid: mcq for mcq in mcq_rows}
                
                # Process each answer using the map (no more DB queries in loop)
                for answer_item in final_answers:
                    try:
                        # Lookup MCQ from map (no DB query)
                        mcq = mcq_map.get(answer_item.question_uuid)
                        
                        if not mcq:
                            failed_count += 1
                            failed_questions.append(answer_item.question_uuid)
                            continue
                        
                        # Convert candidate_answer from string to int
                        try:
                            candidate_option_number = int(answer_item.candidate_answer.strip())
                        except (ValueError, AttributeError):
                            failed_count += 1
                            failed_questions.append(answer_item.question_uuid)
                            continue
                        
                        # Store the option number
                        mcq.candidate_answer = candidate_option_number
                        
                        # Get difficulty and calculate score
                        difficulty = mcq.difficulty.lower()
                        difficulty_score = DIFFICULTY_SCORES.get(difficulty)
                        
                        # Calculate score: weighted score if correct, 0 if incorrect
                        if candidate_option_number == mcq.correct_answer:
                            mcq.score = difficulty_score
                            total_score += difficulty_score
                            correct_answers += 1
                        else:
                            mcq.score = 0
                            incorrect_answers += 1
                        
                        saved_count += 1
                        
                    except Exception as e:
                        logger.error(f"Error processing answer for question {answer_item.question_uuid}: {str(e)}")
                        failed_count += 1
                        failed_questions.append(answer_item.question_uuid)
                        continue
            else:
                # Zero-answer submission: no answers to process, but still mark as submitted
                logger.info(f"Zero-answer submission for candidate {candidate_id}")
            
            # Mark MCQ section as completed in test_session (always, even for zero-answer submission)
            if test_session:
                if test_session.sections_completed is None:
                    test_session.sections_completed = {}
                elif not isinstance(test_session.sections_completed, dict):
                    test_session.sections_completed = {}
                
                test_session.sections_completed["mcq"] = True
                test_session.sections_completed["mcq_submitted_at"] = datetime.utcnow().isoformat()
                test_session.last_activity = datetime.utcnow()
                self.db.commit()
            
            # Track analysis status: mark as IN_PROGRESS if NOT_STARTED
            try:
                from services.analysis_status_service import AnalysisStatusService
                from schemas.analysis import SectionType, AnalysisStatus as AnalysisStatusEnum
                
                status_service = AnalysisStatusService(self.db)
                current_status = status_service.get_status(candidate_id, SectionType.MCQ)
                
                if current_status is None or current_status.status == AnalysisStatusEnum.NOT_STARTED.value:
                    status_service.mark_in_progress(candidate_id, SectionType.MCQ)
                    logger.info(f"[ANALYSIS_STATUS] MCQ analysis transitioned to IN_PROGRESS for candidate {candidate_id}")
                # If already IN_PROGRESS or COMPLETED, do nothing (idempotent)
            except Exception as status_error:
                # Don't fail submission if status tracking fails
                logger.warning(f"Failed to update analysis status for MCQ: {str(status_error)}")
            
            # Enqueue MCQ analysis to background thread (non-blocking)
            import threading
            
            def run_mcq_analysis_async():
                """Helper function to run MCQ analysis in background thread."""
                try:
                    # Create new database session for background task
                    from core.database import SessionLocal
                    background_db = SessionLocal()
                    try:
                        from services.section_analysis_service import analyze_mcq
                        analyze_mcq(candidate_id, background_db)
                    finally:
                        background_db.close()
                except Exception as e:
                    logger.error(f"Error in background MCQ analysis thread for candidate {candidate_id}: {str(e)}", exc_info=True)
            
            try:
                # Start MCQ analysis in background thread
                analysis_thread = threading.Thread(target=run_mcq_analysis_async, daemon=True)
                analysis_thread.start()
                logger.info(f"[BACKGROUND_ANALYSIS] Enqueued MCQ analysis for candidate {candidate_id}")
            except Exception as e:
                logger.warning(f"Failed to enqueue MCQ analysis for candidate {candidate_id}: {str(e)}")
                # Don't fail submission if background task fails to start
            
            # Clear Redis draft after successful submission (always, even for zero-answer submission)
            clear_mcq_draft(candidate_id)
            
            # Build response message
            if not final_answers:
                # Zero-answer submission
                message = "MCQ submitted successfully with zero answers"
            elif failed_count == 0:
                message = f"Successfully submitted {saved_count} answer(s). Total Score: {total_score} points ({correct_answers} correct, {incorrect_answers} incorrect)"
            elif saved_count == 0:
                message = f"Failed to submit all {failed_count} answer(s)"
            else:
                message = f"Submitted {saved_count} answer(s), {failed_count} failed. Total Score: {total_score} points ({correct_answers} correct, {incorrect_answers} incorrect)"
            
            logger.info(f"MCQ submission completed for candidate {candidate_id}: {saved_count} saved, {failed_count} failed")
            
            # For zero-answer submission, always return success=True
            # For non-zero submissions, success depends on whether all answers were saved
            submission_success = True if not final_answers else (failed_count == 0)
            
            return SubmitMCQAnswerResponse(
                success=submission_success,
                message=message,
                saved_count=saved_count,
                failed_count=failed_count,
                failed_questions=failed_questions,
                total_score=total_score,
                total_questions=total_questions_assigned,
                correct_answers=correct_answers,
                incorrect_answers=incorrect_answers,
                submitted_at=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            # Rollback on critical error
            self.db.rollback()
            logger.error(f"Critical error in submit_mcq_answers for candidate {candidate_id}: {str(e)}", exc_info=True)
            return SubmitMCQAnswerResponse(
                success=False,
                message=f"Failed to submit candidate answers. An unexpected error occurred: {str(e)}",
                saved_count=saved_count,
                failed_count=len(request.answers) - saved_count,
                failed_questions=[item.question_uuid for item in request.answers[saved_count:]],
                total_score=total_score,
                total_questions=total_questions_assigned,
                correct_answers=correct_answers,
                incorrect_answers=incorrect_answers,
                submitted_at=datetime.utcnow().isoformat()
            )
    
    def _update_coding_analysis(self, candidate_id: str) -> None:
        """
        Calculate and update coding analysis in interview_analysis_table.
        
        Delegates to standalone analyze_coding function for background-safe execution.
        
        Args:
            candidate_id: UUID of the candidate
        """
        from services.section_analysis_service import analyze_coding
        analyze_coding(candidate_id, self.db)
    
    def _update_cheat_metrics(self, candidate_id: str, integrity_data) -> None:
        """
        Update cheat metrics in interview_analysis_table from integrity data.
        
        Transforms IntegrityData from CompleteTestRequest into cheat_metrics JSONB format
        and saves it to interview_analysis_table.
        
        Args:
            candidate_id: UUID of the candidate
            integrity_data: IntegrityData object from CompleteTestRequest with:
                - multiple_face: "yes" or "no"
                - full_screen_exits: int
                - tab_change: int
        """
        if not integrity_data:
            logger.warning(f"No integrity data provided for candidate {candidate_id}, skipping cheat_metrics update")
            return
        
        try:
            # Transform integrity data to cheat_metrics format
            # Handle both Pydantic model and dict formats
            if hasattr(integrity_data, 'multiple_face'):
                multiple_face = integrity_data.multiple_face
            elif isinstance(integrity_data, dict):
                multiple_face = integrity_data.get('multiple_face', 'no')
            else:
                multiple_face = 'no'
            
            if hasattr(integrity_data, 'full_screen_exits'):
                full_screen_exits = integrity_data.full_screen_exits
            elif isinstance(integrity_data, dict):
                full_screen_exits = integrity_data.get('full_screen_exits', 0)
            else:
                full_screen_exits = 0
            
            if hasattr(integrity_data, 'tab_change'):
                tab_change = integrity_data.tab_change
            elif isinstance(integrity_data, dict):
                tab_change = integrity_data.get('tab_change', 0)
            else:
                tab_change = 0
            
            cheat_metrics = {
                "multiple_face": multiple_face,
                "full_screen_exits": full_screen_exits,
                "tab_change": tab_change
            }
            
            logger.info(f"[INTERVIEW_ANALYSIS] Updating cheat_metrics for candidate {candidate_id}: {cheat_metrics}")
            
            # Get or create interview_analysis record
            interview_analysis = self.db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if interview_analysis:
                # Update existing record
                interview_analysis.cheat_metrics = cheat_metrics
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Updated cheat_metrics for candidate {candidate_id}")
            else:
                # Create new record
                interview_analysis = InterviewAnalysisTable(
                    candidate_id=candidate_id,
                    cheat_metrics=cheat_metrics
                )
                self.db.add(interview_analysis)
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Created new interview_analysis record with cheat_metrics for candidate {candidate_id}")
            
            # Flush to ensure the changes are in the session (but don't commit - let caller handle it)
            self.db.flush()
            
            # Note: Don't commit here - let the calling method handle the transaction
            # This allows cheat_metrics to be part of the same transaction as test completion
            
        except Exception as e:
            logger.error(f"Error updating cheat metrics for candidate {candidate_id}: {str(e)}", exc_info=True)
            # Re-raise the exception so the caller knows it failed
            # The caller can decide whether to fail the entire operation or continue
            raise
    
    async def generate_and_save_interview_summary(self, candidate_id: str) -> None:
        """
        Generate interview summary using LLM and save it to interview_analysis_table.
        
        This function:
        1. Fetches all analysis data from interview_analysis_table
        2. Extracts metadata for MCQ, Coding, System Design, and Integrity
        3. Calls the LLM summary generator
        4. Saves the summary to overall_summary field
        
        Args:
            candidate_id: UUID of the candidate
        """
        try:
            # Get interview analysis record
            logger.info(f"[DATA_SOURCE] 📊 Fetching interview analysis from POSTGRESQL for summary generation for candidate {candidate_id}")
            interview_analysis = self.db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if not interview_analysis:
                logger.warning(f"[DATA_SOURCE] ❌ No interview analysis found in POSTGRESQL for candidate {candidate_id}, cannot generate summary")
                return
            
            logger.info(f"[DATA_SOURCE] ✅ Found interview analysis in POSTGRESQL for candidate {candidate_id}")
            
            # Extract MCQ metadata
            logger.info(f"[DATA_SOURCE] 📥 Extracting MCQ metadata from POSTGRESQL for candidate {candidate_id}")
            mcq_analysis = interview_analysis.mcq_analysis or {}
            mcq_metadata = {
                "score": mcq_analysis.get("score", 0),
                "attempted": mcq_analysis.get("attempted", {"easy": 0, "medium": 0, "hard": 0}),
                "correct": mcq_analysis.get("correct", {"easy": 0, "medium": 0, "hard": 0})
            }
            
            # Extract Coding metadata
            logger.info(f"[DATA_SOURCE] 📥 Extracting coding metadata from POSTGRESQL for candidate {candidate_id}")
            coding_analysis = interview_analysis.coding_analysis or {}
            coding_metadata = {
                "total_score": coding_analysis.get("total_score", 0),
                "time_taken": coding_analysis.get("time_taken", 0),
                "total_submitted": coding_analysis.get("total_submitted", 0),
                "total_correct": coding_analysis.get("total_correct", 0),
                "partially_correct": coding_analysis.get("partially_correct", 0)
            }
            
            # Extract System Design metadata
            logger.info(f"[DATA_SOURCE] 📥 Extracting system design metadata from POSTGRESQL for candidate {candidate_id}")
            system_design_analysis = interview_analysis.system_design_analysis or {}
            system_design_metadata = {
                "score": system_design_analysis.get("score", 0),
                "summary": system_design_analysis.get("summary", "N/A"),
                "key_strengths": system_design_analysis.get("key_strengths", []),
                "areas_of_improvement": system_design_analysis.get("things_to_improve", []),
                "time_taken": system_design_analysis.get("time_taken", 0)  # May not be stored, will be 0 if not available
            }
            
            # Extract Integrity metadata from cheat_metrics
            cheat_metrics = interview_analysis.cheat_metrics or {}
            integrity_metadata = {
                "tab_switch_count": cheat_metrics.get("tab_change", 0),
                "fullscreen_exits_count": cheat_metrics.get("full_screen_exits", 0),
                "multiple_faces": cheat_metrics.get("multiple_face", "no") == "yes"
            }
            
            
            # Generate summary using LLM
            summary = await generate_interview_summary(
                mcq_metadata=mcq_metadata,
                coding_metadata=coding_metadata,
                system_design_metadata=system_design_metadata,
                integrity_metadata=integrity_metadata
            )
            
            # Calculate overall score (average of MCQ, Coding, and System Design)
            mcq_score = mcq_metadata.get("score", 0)
            coding_score = coding_metadata.get("total_score", 0)
            system_design_score = system_design_metadata.get("score", 0)
            
            overall_percentage = round((mcq_score + coding_score + system_design_score) / 3)
            
            # Determine integrity level
            tab_change = cheat_metrics.get("tab_change", 0)
            full_screen_exits = cheat_metrics.get("full_screen_exits", 0)
            multiple_face = cheat_metrics.get("multiple_face", "no")
            
            is_low_integrity = False
            if (tab_change + full_screen_exits) > 2:
                is_low_integrity = True
            if multiple_face == "yes":
                is_low_integrity = True
            
            # Determine result (PASS/FAIL)
            if is_low_integrity:
                result = "FAIL"
            elif overall_percentage > 70:
                result = "PASS"
            else:
                result = "FAIL"
            
            # Save summary, overall_percentage, and result to interview_analysis_table
            interview_analysis.overall_summary = summary
            interview_analysis.overall_percentage = overall_percentage
            interview_analysis.result = result
            self.db.commit()
            
            logger.info(f"[INTERVIEW_ANALYSIS] ✅ Generated and saved overall_summary for candidate {candidate_id}")
            logger.info(f"[INTERVIEW_ANALYSIS] ✅ Overall Score: {overall_percentage}%, Result: {result}, Integrity: {'Low' if is_low_integrity else 'High'}")
            
        except Exception as e:
            logger.error(f"Error generating interview summary for candidate {candidate_id}: {str(e)}", exc_info=True)
            # Don't raise - this is non-critical, don't break test completion
            self.db.rollback()
    
    async def generate_summary_and_send_email(
        self,
        candidate_id: str,
        candidate_email: str,
        candidate_name: str,
        completion_date: datetime
    ) -> None:
        """
        Generate interview summary and send assessment report email sequentially.
        
        This function:
        1. Generates and saves interview summary (must complete first)
        2. Sends assessment report email to candidate (after summary is ready)
        
        Both operations run sequentially to ensure summary is available before email is sent.
        This is designed to be called from a background thread.
        
        Args:
            candidate_id: UUID of the candidate
            candidate_email: Candidate's email address
            candidate_name: Candidate's name
            completion_date: Test completion date/time
        """
        try:
            # Step 1: Generate and save interview summary first
            logger.info(f"[POST_COMPLETION] Generating interview summary for candidate {candidate_id}")
            await self.generate_and_save_interview_summary(candidate_id)
            logger.info(f"[POST_COMPLETION] ✅ Interview summary generated for candidate {candidate_id}")
            
            # Step 2: Send assessment report email after summary is ready
            logger.info(f"[POST_COMPLETION] Sending assessment report email to {candidate_email}")
            email_sent = await email_service.send_assessment_report_email(
                candidate_id=candidate_id,
                candidate_email=candidate_email,
                candidate_name=candidate_name,
                completion_date=completion_date,
                db=self.db
            )
            
            if email_sent:
                logger.info(f"[POST_COMPLETION] ✅ Assessment report email sent to {candidate_email}")
            else:
                logger.warning(f"[POST_COMPLETION] ⚠️ Assessment report email was not sent to {candidate_email} (may not be ready or email disabled)")
                
        except Exception as e:
            logger.error(f"Error in generate_summary_and_send_email for candidate {candidate_id}: {str(e)}", exc_info=True)
            # Don't raise - this is non-critical, don't break test completion
    
    async def _update_system_design_analysis(self, candidate_id: str) -> None:
        """
        Calculate and update system design analysis in interview_analysis_table.
        
        Fully self-contained function that:
        a. Checks if question is assigned - if not, writes ZERO analysis JSON
        b. Checks if any submission exists - if not, writes ZERO analysis JSON
        c. Otherwise generates report and persists analysis JSON
        
        Never leaves analysis JSON as null.
        
        Args:
            candidate_id: UUID of the candidate
        """
        try:
            
            
            # Step a: Check if question is assigned for the section
            logger.info(f"[DATA_SOURCE] 📊 Fetching system design question from POSTGRESQL for candidate {candidate_id}")
            sd_record = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if sd_record:
                logger.info(f"[DATA_SOURCE] ✅ Found system design question in POSTGRESQL for candidate {candidate_id}")
            else:
                logger.info(f"[DATA_SOURCE] ⚠️ No system design question found in POSTGRESQL for candidate {candidate_id}")
            
            if not sd_record:
                # No question assigned - write ZERO analysis JSON
                system_design_analysis = {
                    "score": 0,
                    "summary": "No system design submission"
                }
            else:
                # Step b: Check if any submission exists (canvas or diagram)
                has_submission = bool(sd_record.current_canvas or sd_record.final_diagram)
                
                if not has_submission:
                    # No submission - write ZERO analysis JSON
                    system_design_analysis = {
                        "score": 0,
                        "summary": "No system design submission"
                    }
                else:
                    # Step c: Generate report and build analysis JSON
                    try:
                        from services.system_design_service import SystemDesignService
                        
                        sd_service = SystemDesignService(self.db)
                        # generate_final_report already saves to interview_analysis_table
                        await sd_service.generate_final_report(
                                candidate_id=candidate_id,
                                question_uuid=sd_record.question_uuid
                        )
                        
                        # Verify analysis was saved by generate_final_report
                        saved_analysis = self.db.query(InterviewAnalysisTable).filter(
                            InterviewAnalysisTable.candidate_id == candidate_id
                        ).first()
                        
                        if saved_analysis and saved_analysis.system_design_analysis:
                            # Analysis already saved by generate_final_report, nothing more to do
                            return
                        else:
                            # Fallback: build ZERO analysis JSON if not saved
                            system_design_analysis = {
                                "score": 0,
                                "summary": "No system design submission"
                            }
                    except Exception as e:
                        logger.error(f"Error generating system design report for candidate {candidate_id}: {str(e)}", exc_info=True)
                        # Fallback to ZERO analysis JSON on error
                        system_design_analysis = {
                            "score": 0,
                            "summary": "No system design submission"
                        }
            
            # Get or create interview_analysis record
            logger.info(f"[DATA_SOURCE] 💾 Saving system design analysis to POSTGRESQL (InterviewAnalysisTable) for candidate {candidate_id}")
            interview_analysis = self.db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if interview_analysis:
                # Update existing record
                interview_analysis.system_design_analysis = system_design_analysis
                logger.info(f"[DATA_SOURCE] ✅ Updated system_design_analysis in POSTGRESQL for candidate {candidate_id}")
            else:
                # Create new record
                interview_analysis = InterviewAnalysisTable(
                    candidate_id=candidate_id,
                    system_design_analysis=system_design_analysis
                )
                self.db.add(interview_analysis)
                logger.info(f"[DATA_SOURCE] ✅ Created new interview_analysis record with system_design_analysis in POSTGRESQL for candidate {candidate_id}")
            
            # Commit the analysis update
            self.db.commit()
            logger.info(f"[DATA_SOURCE] ✅ Committed system design analysis to POSTGRESQL for candidate {candidate_id}")

        except Exception as e:
            logger.error(f"Error updating system design analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
            self.db.rollback()
            raise
    
    async def ensure_all_analyses_complete(self, candidate_id: str) -> Dict[str, Any]:
        """
        Ensure all section analyses are complete before test completion.
        
        Pure orchestrator function that checks analysis status for each section:
        - If status is COMPLETED → skip (already done)
        - If status is IN_PROGRESS → skip (already running)
        - If status is NOT_STARTED or missing → mark as IN_PROGRESS and start analysis
        
        This ensures all sections get analyzed even if they were never submitted.
        Zero-score analysis will be generated for unsubmitted sections.
        
        Does NOT check Redis, submissions, or question existence here.
        Those checks are handled by the analysis functions themselves.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Dictionary with results:
            {
                "success": bool,
                "completed_analyses": ["mcq", "coding", ...],
                "skipped_analyses": ["system_design", ...],
                "failed_analyses": [("section", "error_message"), ...]
            }
        """
        
        completed = []
        skipped = []
        failed = []
        
        # Import analysis status service and enums
        from services.analysis_status_service import AnalysisStatusService
        from schemas.analysis import SectionType, AnalysisStatus as AnalysisStatusEnum
        
        status_service = AnalysisStatusService(self.db)
        
        # Get or create interview_analysis record
        logger.info(f"[DATA_SOURCE] 📊 Checking existing analyses in POSTGRESQL (InterviewAnalysisTable) for candidate {candidate_id}")
        interview_analysis = self.db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if not interview_analysis:
            interview_analysis = InterviewAnalysisTable(candidate_id=candidate_id)
            self.db.add(interview_analysis)
            self.db.flush()
            logger.info(f"[DATA_SOURCE] ✅ Created new interview_analysis record in POSTGRESQL for candidate {candidate_id}")
        else:
            logger.info(f"[DATA_SOURCE] ✅ Found existing interview_analysis record in POSTGRESQL for candidate {candidate_id}")
        
        # ============================================================================
        # 1. MCQ Analysis
        # ============================================================================
        logger.info(f"[DATA_SOURCE] 🔍 Checking MCQ analysis in POSTGRESQL for candidate {candidate_id}")
        
        # Check analysis status first (like System Design)
        mcq_status = status_service.get_status(candidate_id, SectionType.MCQ)
        
        if mcq_status and mcq_status.status == AnalysisStatusEnum.COMPLETED.value:
            # Analysis already completed
            skipped.append("mcq")
            logger.info(f"[ENSURE_ANALYSIS] ⏭️  MCQ analysis already completed for {candidate_id}")
        elif mcq_status and mcq_status.status == AnalysisStatusEnum.IN_PROGRESS.value:
            # Analysis in progress - skip (already running)
            skipped.append("mcq")
            logger.info(f"[ENSURE_ANALYSIS] ⏳ MCQ analysis in progress for {candidate_id}, skipping")
        else:
            # Analysis not started or missing - mark IN_PROGRESS and start analysis
            try:
                # Mark as IN_PROGRESS before calling analysis
                status_service.mark_in_progress(candidate_id, SectionType.MCQ)
                logger.info(f"[ANALYSIS_STATUS] MCQ analysis transitioned to IN_PROGRESS for candidate {candidate_id}")
                
                self._update_mcq_analysis(candidate_id)
                completed.append("mcq")
                logger.info(f"[ENSURE_ANALYSIS] ✅ Completed MCQ analysis for {candidate_id}")
            except Exception as e:
                failed.append(("mcq", str(e)))
                logger.error(f"[ENSURE_ANALYSIS] ❌ Failed MCQ analysis: {e}")
        
        # ============================================================================
        # 2. Coding Analysis
        # ============================================================================
        self.db.refresh(interview_analysis)
        logger.info(f"[DATA_SOURCE] 🔍 Checking coding analysis in POSTGRESQL for candidate {candidate_id}")
        
        # Check analysis status first (like System Design)
        coding_status = status_service.get_status(candidate_id, SectionType.CODING)
        
        if coding_status and coding_status.status == AnalysisStatusEnum.COMPLETED.value:
            # Analysis already completed
            skipped.append("coding")
            logger.info(f"[ENSURE_ANALYSIS] ⏭️  Coding analysis already completed for {candidate_id}")
        elif coding_status and coding_status.status == AnalysisStatusEnum.IN_PROGRESS.value:
            # Analysis in progress - skip (already running)
            skipped.append("coding")
            logger.info(f"[ENSURE_ANALYSIS] ⏳ Coding analysis in progress for {candidate_id}, skipping")
        else:
            # Analysis not started or missing - mark IN_PROGRESS and start analysis
            try:
                # Mark as IN_PROGRESS before calling analysis
                status_service.mark_in_progress(candidate_id, SectionType.CODING)
                logger.info(f"[ANALYSIS_STATUS] Coding analysis transitioned to IN_PROGRESS for candidate {candidate_id}")
                
                self._update_coding_analysis(candidate_id)
                completed.append("coding")
                logger.info(f"[ENSURE_ANALYSIS] ✅ Completed Coding analysis for {candidate_id}")
            except Exception as e:
                failed.append(("coding", str(e)))
                logger.error(f"[ENSURE_ANALYSIS] ❌ Failed Coding analysis: {e}")
        
        # ============================================================================
        # 3. System Design Analysis (Background - Non-Blocking)
        # ============================================================================
        self.db.refresh(interview_analysis)
        logger.info(f"[DATA_SOURCE] 🔍 Checking system design analysis in POSTGRESQL for candidate {candidate_id}")
        
        # Check analysis status
        sd_status = status_service.get_status(candidate_id, SectionType.SYSTEM_DESIGN)
        
        if sd_status and sd_status.status == AnalysisStatusEnum.COMPLETED.value:
            # Analysis already completed
            skipped.append("system_design")
            logger.info(f"[ENSURE_ANALYSIS] ⏭️  System Design analysis already completed for {candidate_id}")
        elif sd_status and sd_status.status == AnalysisStatusEnum.IN_PROGRESS.value:
            # Analysis in progress - don't wait, skip
            skipped.append("system_design")
            logger.info(f"[ENSURE_ANALYSIS] ⏳ System Design analysis in progress for {candidate_id}, skipping (non-blocking)")
        else:
            # Analysis not started - enqueue to background and skip (don't block)
            try:
                # Mark as IN_PROGRESS
                status_service.mark_in_progress(candidate_id, SectionType.SYSTEM_DESIGN)
                logger.info(f"[ANALYSIS_STATUS] System Design analysis transitioned to IN_PROGRESS for candidate {candidate_id}")
                
                # Enqueue to background thread
                import threading
                
                def run_system_design_analysis_async():
                    """Helper function to run System Design analysis in background thread."""
                    try:
                        from core.database import SessionLocal
                        background_db = SessionLocal()
                        try:
                            from services.section_analysis_service import analyze_system_design
                            analyze_system_design(candidate_id, background_db)
                        finally:
                            background_db.close()
                    except Exception as e:
                        logger.error(f"Error in background System Design analysis thread for candidate {candidate_id}: {str(e)}", exc_info=True)
                
                analysis_thread = threading.Thread(target=run_system_design_analysis_async, daemon=True)
                analysis_thread.start()
                logger.info(f"[BACKGROUND_ANALYSIS] Enqueued System Design analysis for candidate {candidate_id}")
                
                skipped.append("system_design")
                logger.info(f"[ENSURE_ANALYSIS] 🚀 System Design analysis enqueued to background for {candidate_id}")
            except Exception as e:
                failed.append(("system_design", str(e)))
                logger.error(f"[ENSURE_ANALYSIS] ❌ Failed to enqueue System Design analysis: {e}")
        
        return {
            "success": len(failed) == 0,
            "completed_analyses": completed,
            "skipped_analyses": skipped,
            "failed_analyses": failed
        }
    
    def _assign_system_design(self, candidate_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Assign system design question to candidate.
        
        This function runs in a separate thread and creates its own DB session
        because SQLAlchemy sessions are NOT thread-safe.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Tuple of (result_dict, error_message)
            - result_dict: Success result dict or None on error
            - error_message: Error message string or None on success
        """
        # Create a new DB session for this thread
        # SQLAlchemy sessions are NOT thread-safe, so each parallel task needs its own session
        from core.database import SessionLocal
        db = SessionLocal()
        
        try:
            
            assignment_service = QuestionAssignmentService(db)
            result = assignment_service.assign_question_to_candidate(
                candidate_id=candidate_id
            )
            
            if result.get("success"):
                return result, None
            else:
                error_msg = f"System design question assignment failed: {result.get('message', 'Unknown error')}"
                return None, error_msg
                
        except Exception as e:
            error_msg = f"System design question assignment error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
        finally:
            # Always close the DB session, even if an error occurred
            db.close()
    
    def _assign_coding(self, candidate_id: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Assign coding questions to candidate.
        
        This function runs in a separate thread and creates its own DB session
        because SQLAlchemy sessions are NOT thread-safe.
        
        Args:
            candidate_id: UUID of the candidate
            
        Returns:
            Tuple of (result_dict, error_message)
            - result_dict: Success result dict or None on error
            - error_message: Error message string or None on success
        """
        # Create a new DB session for this thread
        # SQLAlchemy sessions are NOT thread-safe, so each parallel task needs its own session
        from core.database import SessionLocal
        from core.config import settings
        db = SessionLocal()
        
        try:
            
            coding_service = CodingQuestionAssignmentService(db)
            result = coding_service.assign_coding_questions_to_candidate(
                candidate_id=candidate_id,
                use_random=settings.RANDOM_CODING_QUESTIONS
            )
            
            if result.get("success"):
                return result, None
            else:
                error_msg = f"Coding question assignment failed: {result.get('message', 'Unknown error')}"
                return None, error_msg
                
        except Exception as e:
            error_msg = f"Coding question assignment error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
        finally:
            # Always close the DB session, even if an error occurred
            db.close()
    
    async def _generate_and_save_mcqs(self, candidate_id: str, resume: str, job_description: str, job_grade: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """
        Generate and save MCQ questions for candidate.
        
        This function creates its own DB session because SQLAlchemy sessions are NOT thread-safe.
        Since this is an async function, it runs concurrently with other async tasks in the same event loop.
        
        Args:
            candidate_id: UUID of the candidate
            resume: Candidate's resume text
            job_description: Job description text
            job_grade: Job grade (T2 or T3)
            
        Returns:
            Tuple of (result_dict, error_message)
            - result_dict: Success result dict or None on error
            - error_message: Error message string or None on success
        """
        # Create a new DB session for this thread
        # SQLAlchemy sessions are NOT thread-safe, so each parallel task needs its own session
        from core.database import SessionLocal
        db = SessionLocal()
        
        try:
            from services.mcq_generation_service import MCQGenerationService
            mcq_service = MCQGenerationService(db)
            
            # Create request for MCQ generation
            mcq_request = GenerateMCQRequest(
                resume=resume,
                job_description=job_description,
                grade=job_grade
            )
            
            logger.info(f"[MCQ GENERATION] Generating MCQ questions for candidate {candidate_id}")
            
            # Generate questions (async operation)
            generation_result = await mcq_service.generate_questions(mcq_request)
            questions = generation_result.get("questions", [])
            
            if questions:
                # Save generated questions to database
                save_result = mcq_service.save_generated_questions(
                    candidate_id=candidate_id,
                    questions=questions
                )
                if save_result.get("success"):
                    result = {
                        "success": True,
                        "message": f"Generated and saved {save_result.get('saved_count', 0)} MCQ questions"
                    }
                    logger.info(f"[MCQ GENERATION] Successfully generated and saved {save_result.get('saved_count', 0)} MCQ questions for candidate {candidate_id}")
                    return result, None
                else:
                    error_msg = f"MCQ generation succeeded but saving failed: {save_result.get('message', 'Unknown error')}"
                    return None, error_msg
            else:
                error_msg = "MCQ generation returned no questions"
                return None, error_msg
                
        except Exception as e:
            error_msg = f"MCQ generation error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return None, error_msg
        finally:
            # Always close the DB session, even if an error occurred
            db.close()
    
    def _process_task_result(self, task_name: str, candidate_id: str, result: Any, error_messages: List[str]) -> Optional[Dict[str, Any]]:
        """
        Centralized helper to process task results from parallel execution.
        
        Handles both exception results and tuple results (result, error) consistently.
        This eliminates repeated error handling logic and ensures uniform error reporting.
        
        Args:
            task_name: Name of the task (for logging)
            candidate_id: UUID of the candidate (for logging)
            result: Task result - either Exception or Tuple[Optional[Dict], Optional[str]]
            error_messages: List to append error messages to
            
        Returns:
            Result dictionary if successful, None otherwise
        """
        if isinstance(result, Exception):
            error_msg = f"{task_name} error: {str(result)}"
            error_messages.append(error_msg)
            logger.error(f"{task_name} failed for candidate {candidate_id}: {result}", exc_info=True)
            return None
        
        # Result is a tuple: (result_dict, error_message)
        result_dict, error_message = result
        
        if error_message:
            error_messages.append(error_message)
            logger.error(f"{task_name} failed for candidate {candidate_id}: {error_message}")
            return None
        
        return result_dict
    
    async def _assign_questions_and_generate_mcq(self, candidate_id: str, candidate: Candidate, scheduled_date_for_message: datetime) -> tuple:
        """
        Helper function to assign questions and generate MCQ questions in parallel.
        Shared logic between schedule-based and immediate start flows.
        
        This function runs three independent tasks in parallel:
        1. System design question assignment
        2. Coding question assignment  
        3. MCQ generation and saving
        
        All tasks run concurrently using asyncio.gather() to reduce latency.
        Each task creates its own DB session since SQLAlchemy sessions are NOT thread-safe.
        
        Args:
            candidate_id: UUID of the candidate
            candidate: Candidate object
            scheduled_date_for_message: datetime to use in response message
            
        Returns:
            Tuple of (error_messages list, system_design_result, mcq_result, coding_result)
        """
        # Get job information for MCQ generation (needed before parallel execution)
        assignment = self.db.query(RecruiterAdminCandidate).filter(
            RecruiterAdminCandidate.candidate_id == candidate_id
        ).first()
        
        logger.info(f"[QUESTION ASSIGNMENT] Starting parallel question assignment for candidate {candidate_id}")
        logger.debug(f"[QUESTION ASSIGNMENT] Job role: {assignment.job.job_role}, Grade: {assignment.job.grade}")
        
        # Prepare data needed for parallel tasks
        error_messages = []
        system_design_result = None
        mcq_result = None
        coding_result = None
        
        job_grade = assignment.job.grade
        
        tasks = {
            "system_design": asyncio.to_thread(self._assign_system_design, candidate_id),
            "coding": asyncio.to_thread(self._assign_coding, candidate_id),
            "mcq": self._generate_and_save_mcqs(
                candidate_id=candidate_id,
                resume=candidate.resume,
                job_description=assignment.job.job_description,
                job_grade=job_grade
            )
        }
        
        # Run all tasks in parallel using asyncio.gather
        # return_exceptions=True ensures that if one task fails, others continue
        # This maintains task isolation - one failure doesn't kill others
        results = await asyncio.gather(
            tasks["system_design"],
            tasks["coding"],
            tasks["mcq"],
            return_exceptions=True
        )
        
        # Process results using centralized helper for consistent error handling
        system_design_result = self._process_task_result(
            "System design question assignment",
            candidate_id,
            results[0],
            error_messages
        )
        
        coding_result = self._process_task_result(
            "Coding question assignment",
            candidate_id,
            results[1],
            error_messages
        )
        
        mcq_result = self._process_task_result(
            "MCQ generation",
            candidate_id,
            results[2],
            error_messages
        )
        
        logger.info(f"[QUESTION ASSIGNMENT] Completed parallel question assignment for candidate {candidate_id}. "
                    f"Errors: {len(error_messages)}, System Design: {system_design_result is not None}, "
                    f"Coding: {coding_result is not None}, MCQ: {mcq_result is not None}")
        
        return error_messages, system_design_result, mcq_result, coding_result

    async def save_test_schedule_with_scheduled_date(self, candidate_id: str, request: ScheduleTestRequest) -> ScheduleTestResponse:
        """
        Save test schedule for a candidate according to scheduled_date (SCHEDULE-BASED FLOW).
        
        This method:
        1. Updates the candidate's scheduled_date and status to 'scheduled'
        2. Calls QuestionAssignmentService to assign a system design question (parallel)
        3. Calls CodingQuestionAssignmentService to assign coding questions (parallel)
        4. Generates MCQ questions using RAG (parallel)
        5. Sends test invitation email AFTER questions are generated and assigned
        
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
            
            # Allow scheduling for candidates in any status (removed status check)
            
            # Convert scheduled_date to IST naive datetime for storage
            # The incoming datetime is timezone-aware (e.g., 2025-12-16T10:00:00+05:30)
            # We need to convert it to IST timezone and make it naive so it stores correctly
            scheduled_date_to_store = request.scheduled_date
            if scheduled_date_to_store.tzinfo is not None:
                # Convert to IST timezone (UTC+5:30)
                ist_timezone = timezone(timedelta(hours=5, minutes=30))
                # Convert to IST
                ist_datetime = scheduled_date_to_store.astimezone(ist_timezone)
                # Make it naive (remove timezone) so it stores as IST time directly
                scheduled_date_to_store = ist_datetime.replace(tzinfo=None)
            
            # Update candidate's scheduled_date and status (SCHEDULE-BASED: uses request.scheduled_date)
            candidate.scheduled_date = scheduled_date_to_store
            candidate.status = 'scheduled'
            
            # Commit the schedule update first
            self.db.commit()
            
            # Assign questions and generate MCQ (shared logic)
            error_messages, system_design_result, mcq_result, coding_result = await self._assign_questions_and_generate_mcq(
                candidate_id, candidate, request.scheduled_date
            )
            
            # Send test invitation email AUTOMATICALLY after questions are generated and assigned
            try:
                # Get job information and recruiter details
                assignment = self.db.query(RecruiterAdminCandidate).filter(
                    RecruiterAdminCandidate.candidate_id == candidate_id
                ).first()
                
                if assignment:
                    job = self.db.query(Job).filter(Job.job_id == assignment.job_id).first()
                    job_role = job.job_role if job else "Technical Interview"
                    
                    # Get recruiter details
                    from models.recruiter_admin import RecruiterAdmin
                    recruiter = self.db.query(RecruiterAdmin).filter(
                        RecruiterAdmin.email_id == assignment.recruiter_admin_email
                    ).first()
                    
                    # Generate test link for candidate
                    from core.config import settings
                    test_link = f"{settings.FRONTEND_URL}/test/scheduled?candidate_id={candidate_id}"
                    
                    # Send notifications (async, non-blocking)
                    # Use threading to run async function in background
                    import threading
                    
                    def send_notifications_async():
                        """Helper function to run async notifications in background thread."""
                        try:
                            # Create new database session for background thread
                            # (SQLAlchemy sessions are not thread-safe)
                            from core.database import SessionLocal
                            db_session = SessionLocal()
                            
                            try:
                                # Run all notifications in parallel
                                async def send_all_notifications():
                                    # 1. Send candidate email
                                    email_task = email_service.send_test_invitation_email(
                                        candidate_email=candidate.email_id,
                                        candidate_name=candidate.name,
                                        candidate_id=candidate_id,
                                        job_role=job_role,
                                        scheduled_date=request.scheduled_date
                                    )
                                    
                                    # 2. Send recruiter email (if recruiter exists)
                                    recruiter_email_task = None
                                    
                                    if recruiter:
                                        recruiter_email_task = email_service.send_recruiter_test_notification_email(
                                            recruiter_email=recruiter.email_id,
                                            recruiter_name=recruiter.name,
                                            candidate_name=candidate.name,
                                            candidate_email=candidate.email_id,
                                            candidate_reference_number=candidate.candidate_reference_number,
                                            job_role=job_role,
                                            scheduled_date=request.scheduled_date
                                        )
                                    
                                    # Wait for all tasks to complete
                                    tasks = [email_task]
                                    if recruiter_email_task:
                                        tasks.append(recruiter_email_task)
                                    
                                    await asyncio.gather(*tasks, return_exceptions=True)
                                
                                asyncio.run(send_all_notifications())
                            finally:
                                # Close database session
                                db_session.close()
                        except Exception as e:
                            logger.error(f"Error in background notification thread: {str(e)}")
                    
                    # Start notification sending in background thread
                    notification_thread = threading.Thread(target=send_notifications_async, daemon=True)
                    notification_thread.start()
                    
                    logger.info(f"Test invitation notifications (email) queued for candidate {candidate_id} and recruiter after questions were assigned")
            except Exception as e:
                # Don't fail scheduling if notifications fail
                logger.error(f"Failed to queue test invitation notifications: {str(e)}")
            
            # Build response message - format stored IST datetime with IST timezone for display
            ist_timezone = timezone(timedelta(hours=5, minutes=30))
            stored_datetime_ist = scheduled_date_to_store.replace(tzinfo=ist_timezone)
            scheduled_date_iso = stored_datetime_ist.isoformat()
            
            base_message = f"Test scheduled successfully for {scheduled_date_iso}"
            if error_messages:
                base_message += f". Warnings: {'; '.join(error_messages)}"
            
            return ScheduleTestResponse(
                success=True,
                message=base_message,
                scheduled_date=scheduled_date_iso
            )
            
        except Exception as e:
            # Rollback on error
            self.db.rollback()
            return ScheduleTestResponse(
                success=False,
                message=f"Failed to save test schedule. An unexpected error occurred: {str(e)}",
                scheduled_date=None
            )

    async def save_test_schedule_immediate_start(self, candidate_id: str, request: ScheduleTestRequest) -> ScheduleTestResponse:
        """
        Save test schedule for a candidate WITHOUT using scheduled_date (IMMEDIATE START FLOW).
        
        This method:
        1. Updates the candidate's status to 'scheduled' (scheduled_date is NOT set here - will be set when test starts)
        2. Calls QuestionAssignmentService to assign a system design question (parallel)
        3. Calls CodingQuestionAssignmentService to assign coding questions (parallel)
        4. Generates MCQ questions using RAG (parallel)
        5. Sends test invitation email AFTER questions are generated and assigned
        
        NOTE: scheduled_date will be set to current time when test actually starts (in start_test endpoint).
        
        Args:
            candidate_id: UUID of the candidate
            request: ScheduleTestRequest with scheduled_date (used for email only, not saved to DB)
            
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
            
            # Allow scheduling for candidates in any status (removed status check)
            
            # IMMEDIATE START FLOW: Do NOT save scheduled_date here - it will be set when test starts
            # candidate.scheduled_date = request.scheduled_date  # COMMENTED OUT - will be set at test start
            candidate.status = 'scheduled'
            
            # Commit the schedule update first
            self.db.commit()
            
            # Assign questions and generate MCQ (shared logic)
            # Use request.scheduled_date for message, but it's not saved to DB
            error_messages, system_design_result, mcq_result, coding_result = await self._assign_questions_and_generate_mcq(
                candidate_id, candidate, request.scheduled_date
            )
            
            # Send test invitation email AUTOMATICALLY after questions are generated and assigned
            try:
                # Get job information and recruiter details
                assignment = self.db.query(RecruiterAdminCandidate).filter(
                    RecruiterAdminCandidate.candidate_id == candidate_id
                ).first()
                
                if assignment:
                    job = self.db.query(Job).filter(Job.job_id == assignment.job_id).first()
                    job_role = job.job_role if job else "Technical Interview"
                    
                    # Get recruiter details
                    from models.recruiter_admin import RecruiterAdmin
                    recruiter = self.db.query(RecruiterAdmin).filter(
                        RecruiterAdmin.email_id == assignment.recruiter_admin_email
                    ).first()
                    
                    # Generate test link for candidate
                    from core.config import settings
                    test_link = f"{settings.FRONTEND_URL}/test/scheduled?candidate_id={candidate_id}"
                    
                    # Send notifications (async, non-blocking)
                    # Use threading to run async function in background
                    import threading
                    
                    def send_notifications_async():
                        """Helper function to run async notifications in background thread."""
                        try:
                            # Create new database session for background thread
                            # (SQLAlchemy sessions are not thread-safe)
                            from core.database import SessionLocal
                            db_session = SessionLocal()
                            
                            try:
                                # Run all notifications in parallel
                                async def send_all_notifications():
                                    # 1. Send candidate email
                                    email_task = email_service.send_test_invitation_email(
                                        candidate_email=candidate.email_id,
                                        candidate_name=candidate.name,
                                        candidate_id=candidate_id,
                                        job_role=job_role,
                                        scheduled_date=request.scheduled_date
                                    )
                                    
                                    # 2. Send recruiter email (if recruiter exists)
                                    recruiter_email_task = None
                                    
                                    if recruiter:
                                        recruiter_email_task = email_service.send_recruiter_test_notification_email(
                                            recruiter_email=recruiter.email_id,
                                            recruiter_name=recruiter.name,
                                            candidate_name=candidate.name,
                                            candidate_email=candidate.email_id,
                                            candidate_reference_number=candidate.candidate_reference_number,
                                            job_role=job_role,
                                            scheduled_date=request.scheduled_date
                                        )
                                    
                                    # Wait for all tasks to complete
                                    tasks = [email_task]
                                    if recruiter_email_task:
                                        tasks.append(recruiter_email_task)
                                    
                                    await asyncio.gather(*tasks, return_exceptions=True)
                                
                                asyncio.run(send_all_notifications())
                            finally:
                                # Close database session
                                db_session.close()
                        except Exception as e:
                            logger.error(f"Error in background notification thread: {str(e)}")
                    
                    # Start notification sending in background thread
                    notification_thread = threading.Thread(target=send_notifications_async, daemon=True)
                    notification_thread.start()
                    
                    logger.info(f"Test invitation notifications (email) queued for candidate {candidate_id} and recruiter after questions were assigned")
            except Exception as e:
                # Don't fail scheduling if notifications fail
                logger.error(f"Failed to queue test invitation notifications: {str(e)}")
            
            # Build response message
            base_message = f"Test scheduled successfully (scheduled_date will be set when test starts)"
            if error_messages:
                base_message += f". Warnings: {'; '.join(error_messages)}"
            
            return ScheduleTestResponse(
                success=True,
                message=base_message,
                scheduled_date=request.scheduled_date.isoformat() if request.scheduled_date else None
            )
            
        except Exception as e:
            # Rollback on error
            self.db.rollback()
            return ScheduleTestResponse(
                success=False,
                message=f"Failed to save test schedule. An unexpected error occurred: {str(e)}",
                scheduled_date=None
            )

    async def save_test_schedule(self, candidate_id: str, request: ScheduleTestRequest) -> ScheduleTestResponse:
        """
        Save test schedule for a candidate and assign system design question, coding questions, and generate MCQ questions.
        
        This is a wrapper that calls the appropriate function based on the flow you want to use.
        Currently set to use SCHEDULE-BASED FLOW (scheduled_date set during scheduling).
        
        To switch between flows, change the function call below:
        - save_test_schedule_with_scheduled_date: scheduled_date set during scheduling (current)
        - save_test_schedule_immediate_start: scheduled_date set when test starts (commented out)
        
        Args:
            candidate_id: UUID of the candidate
            request: ScheduleTestRequest with scheduled_date
            
        Returns:
            ScheduleTestResponse with success status and scheduled_date
        """
        # SCHEDULE-BASED FLOW: scheduled_date is set during scheduling
        return await self.save_test_schedule_with_scheduled_date(candidate_id, request)
        
        # IMMEDIATE START FLOW: scheduled_date will be set when test starts (commented out)
        # return await self.save_test_schedule_immediate_start(candidate_id, request)

