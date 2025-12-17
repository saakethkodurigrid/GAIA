"""
Interview service for managing interviews.
"""
import logging
import asyncio
import random
import threading
from datetime import datetime, date, timezone, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, func
from models.candidate import Candidate
from models.recruiter_admin_candidate import RecruiterAdminCandidate
from models.job import Job
from models.interview_mcq import InterviewMCQ
from models.interview_coding import InterviewCoding
from models.coding_question_bank import CodingQuestionBank
from models.interview_analysis_table import InterviewAnalysisTable
from schemas.admin import ListInterviewsResponse, InterviewResponse
from schemas.mcq import MCQQuestionsResponse, MCQQuestionResponse, SaveMCQAnswerRequest, SaveMCQAnswerResponse, GenerateMCQRequest
from schemas.candidate import ScheduleTestRequest, ScheduleTestResponse
from services.email_service import email_service
from services.calendar_service import calendar_service

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
        Save or update candidate's answers for multiple MCQ questions and calculate scores.
        
        For each answer:
        - Compares candidate_answer with correct_answer
        - Sets score based on difficulty: hard=3, medium=2, easy=1
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
        
        # Define difficulty scoring weights
        DIFFICULTY_SCORES = {
            "hard": 3,
            "medium": 2,
            "easy": 1
        }
        
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
                    
                    # Convert candidate_answer from string to int
                    # Frontend sends option number as string (e.g., "1", "2", "3", "4")
                    try:
                        candidate_option_number = int(answer_item.candidate_answer.strip())
                    except (ValueError, AttributeError):
                        # Invalid format, mark as failed
                        failed_count += 1
                        failed_questions.append(answer_item.question_uuid)
                        continue
                    
                    # Store the option number
                    mcq.candidate_answer = candidate_option_number
                    
                    # Get difficulty and calculate score based on difficulty
                    difficulty = (mcq.difficulty or "medium").lower()
                    difficulty_score = DIFFICULTY_SCORES.get(difficulty, 1)  # Default to 1 if difficulty is invalid
                    
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
                    # Log error for this specific question but continue with others
                    failed_count += 1
                    failed_questions.append(answer_item.question_uuid)
                    continue
            
            # Commit all changes at once
            self.db.commit()
            
            # Update candidate last_activity if test is in progress
            try:
                candidate = self.db.query(Candidate).filter(
                    Candidate.candidate_id == candidate_id,
                    Candidate.status == 'in progress'
                ).first()
                if candidate and candidate.test_session:
                    from datetime import datetime
                    candidate.test_session.last_activity = datetime.utcnow()
                    self.db.commit()
            except Exception as e:
                # Don't fail if activity update fails
                logger.warning(f"Failed to update candidate activity: {str(e)}")
            
            # Log successful save with evaluation results
            print("=== MCQ ANSWERS SAVED SUCCESSFULLY (BACKEND SERVICE) ===")
            print(f"Candidate ID: {candidate_id}")
            print(f"Total Questions Processed: {saved_count + failed_count}")
            print(f"Successfully Saved: {saved_count}")
            print(f"Failed: {failed_count}")
            print(f"Total Score: {total_score} points")
            print(f"Correct Answers: {correct_answers}")
            print(f"Incorrect Answers: {incorrect_answers}")
            if failed_questions:
                print(f"Failed Question UUIDs: {failed_questions}")
            
            # Log detailed results for each saved question
            print("\nDetailed Results:")
            for answer_item in request.answers:
                if answer_item.question_uuid not in failed_questions:
                    mcq = self.db.query(InterviewMCQ).filter(
                        InterviewMCQ.uuid == answer_item.question_uuid,
                        InterviewMCQ.candidate_id == candidate_id
                    ).first()
                    if mcq:
                        difficulty = (mcq.difficulty or "medium").lower()
                        is_correct = mcq.candidate_answer == mcq.correct_answer
                        print(f"  Question UUID: {answer_item.question_uuid}")
                        print(f"    Candidate Answer: {mcq.candidate_answer}")
                        print(f"    Correct Answer: {mcq.correct_answer}")
                        print(f"    Difficulty: {difficulty}")
                        print(f"    Score: {mcq.score}")
                        print(f"    Correct: {is_correct}")
            print("=========================================================")
            
            # Calculate and save MCQ analysis to interview_analysis_table
            try:
                self._update_mcq_analysis(candidate_id)
            except Exception as e:
                # Don't fail the save operation if analysis update fails
                logger.warning(f"Failed to update MCQ analysis for candidate {candidate_id}: {str(e)}")
            
            # Build response message
            if failed_count == 0:
                message = f"Successfully saved {saved_count} answer(s). Total Score: {total_score} points ({correct_answers} correct, {incorrect_answers} incorrect)"
            elif saved_count == 0:
                message = f"Failed to save all {failed_count} answer(s)"
            else:
                message = f"Saved {saved_count} answer(s), {failed_count} failed. Total Score: {total_score} points ({correct_answers} correct, {incorrect_answers} incorrect)"
            
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
    
    def _update_mcq_analysis(self, candidate_id: str) -> None:
        """
        Calculate and update MCQ analysis in interview_analysis_table.
        
        Calculates:
        - score: Normalized score out of 100 (actual_score / max_possible_score * 100)
        - time_taken: Duration in seconds from test_session.section_timings
        - attempted: Count of attempted questions by difficulty
        - correct: Count of correct answers by difficulty
        
        Args:
            candidate_id: UUID of the candidate
        """
        try:
            # Define difficulty scoring weights (same as in save_mcq_answers)
            DIFFICULTY_SCORES = {
                "hard": 3,
                "medium": 2,
                "easy": 1
            }
            
            # Get all MCQ questions for this candidate
            all_mcqs = self.db.query(InterviewMCQ).filter(
                InterviewMCQ.candidate_id == candidate_id
            ).all()
            
            if not all_mcqs:
                logger.warning(f"No MCQ questions found for candidate {candidate_id}")
                return
            
            # Initialize counters
            attempted = {"easy": 0, "medium": 0, "hard": 0}
            correct = {"easy": 0, "medium": 0, "hard": 0}
            total_score = 0
            max_possible_score = 0
            
            # Calculate scores and counts
            for mcq in all_mcqs:
                difficulty = (mcq.difficulty or "medium").lower()
                difficulty_score = DIFFICULTY_SCORES.get(difficulty, 1)
                
                # Add to max possible score (all questions)
                max_possible_score += difficulty_score
                
                # Check if question was attempted
                if mcq.candidate_answer is not None:
                    # Count as attempted
                    attempted[difficulty] = attempted.get(difficulty, 0) + 1
                    
                    # Check if answer is correct
                    if mcq.candidate_answer == mcq.correct_answer:
                        total_score += difficulty_score
                        correct[difficulty] = correct.get(difficulty, 0) + 1
            
            # Calculate normalized score (0-100)
            if max_possible_score > 0:
                normalized_score = round((total_score / max_possible_score) * 100, 2)
            else:
                normalized_score = 0.0
            
            # Get time taken from test_session
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            time_taken = 0
            # Query test_session directly to avoid relationship issues (InstrumentedList)
            from models.test_session import TestSession
            test_session = self.db.query(TestSession).filter(
                TestSession.candidate_id == candidate_id
            ).first()
            
            if candidate and test_session and test_session.section_timings:
                section_timings = test_session.section_timings
                if isinstance(section_timings, dict) and "mcq" in section_timings:
                    mcq_timing = section_timings["mcq"]
                    if isinstance(mcq_timing, dict) and "duration_seconds" in mcq_timing:
                        time_taken = mcq_timing["duration_seconds"]
                    # If duration_seconds not available, calculate from started_at
                    elif isinstance(mcq_timing, dict) and "started_at" in mcq_timing:
                        try:
                            started_at_str = mcq_timing["started_at"]
                            started_at = datetime.fromisoformat(started_at_str)
                            time_taken = int((datetime.utcnow() - started_at).total_seconds())
                        except Exception as e:
                            logger.warning(f"Failed to calculate time_taken from started_at: {str(e)}")
            
            # Build MCQ analysis JSON
            mcq_analysis = {
                "score": float(normalized_score),
                "time_taken": int(time_taken),
                "attempted": {
                    "easy": int(attempted.get("easy", 0)),
                    "medium": int(attempted.get("medium", 0)),
                    "hard": int(attempted.get("hard", 0))
                },
                "correct": {
                    "easy": int(correct.get("easy", 0)),
                    "medium": int(correct.get("medium", 0)),
                    "hard": int(correct.get("hard", 0))
                }
            }
            
            # Get or create interview_analysis record
            interview_analysis = self.db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if interview_analysis:
                # Update existing record
                interview_analysis.mcq_analysis = mcq_analysis
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Updated mcq_analysis for candidate {candidate_id}")
            else:
                # Create new record
                interview_analysis = InterviewAnalysisTable(
                    candidate_id=candidate_id,
                    mcq_analysis=mcq_analysis
                )
                self.db.add(interview_analysis)
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Created new interview_analysis record with mcq_analysis for candidate {candidate_id}")
            
            # Commit the analysis update
            self.db.commit()
            
            # Try to send assessment report email if all analyses are ready
            try:
                import threading
                import asyncio
                from services.email_service import email_service
                
                def try_send_email_async():
                    """Helper function to run async email sending in background thread."""
                    try:
                        # Create a new database session for the email thread
                        from core.database import get_db
                        db_gen = get_db()
                        db_email = next(db_gen)
                        try:
                            asyncio.run(
                                email_service.try_send_assessment_report_email_if_ready(
                                    candidate_id=candidate_id,
                                    db=db_email
                                )
                            )
                        finally:
                            db_email.close()
                    except Exception as e:
                        logger.error(f"Error in background email thread for candidate {candidate_id}: {str(e)}", exc_info=True)
                
                # Start email check in background thread (non-blocking)
                email_thread = threading.Thread(target=try_send_email_async, daemon=True)
                email_thread.start()
                logger.info(f"Triggered email check for candidate {candidate_id} after MCQ analysis update")
            except Exception as e:
                # Don't fail if email trigger fails
                logger.warning(f"Failed to trigger email check for candidate {candidate_id}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error updating MCQ analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
            # Don't raise - let the calling method handle it
            raise
    
    def _update_coding_analysis(self, candidate_id: str) -> None:
        """
        Calculate and update coding analysis in interview_analysis_table.
        
        Calculates:
        - total_score: Normalized score out of 100 (with difficulty weightage)
        - time_taken: Duration in seconds from test_session.section_timings
        - total_submitted: Count of submitted coding questions
        - total_correct: Count of questions where all test cases passed
        - partially_correct: Count of questions where some but not all test cases passed
        
        Args:
            candidate_id: UUID of the candidate
        """
        try:
            # Define difficulty scoring weights (same as MCQ)
            DIFFICULTY_SCORES = {
                "hard": 3,
                "medium": 2,
                "easy": 1
            }
            
            # Get all coding records for this candidate (both submitted and not attempted)
            all_coding_records = self.db.query(InterviewCoding).filter(
                InterviewCoding.candidate_id == candidate_id
            ).all()
            
            # Filter to get only submitted questions (where score is not None)
            coding_submissions = [record for record in all_coding_records if record.score is not None]
            
            if not all_coding_records:
                logger.warning(f"No coding questions assigned for candidate {candidate_id}")
                # Still create analysis with zeros
                coding_analysis = {
                    "total_score": 0.0,
                    "time_taken": 0,
                    "total_submitted": 0,
                    "total_correct": 0,
                    "partially_correct": 0
                }
            else:
                # Initialize counters
                total_submitted = len(coding_submissions)  # Only count questions with score (submitted)
                total_correct = 0
                partially_correct = 0
                total_weighted_actual_score = 0
                total_weighted_max_score = 0
                
                # Process all assigned questions to calculate max possible score
                # (including not attempted ones for proper normalization)
                for coding_record in all_coding_records:
                    # Get question details from CodingQuestionBank
                    question = self.db.query(CodingQuestionBank).filter(
                        CodingQuestionBank.uuid == coding_record.question_uuid
                    ).first()
                    
                    if not question:
                        logger.warning(f"Question {coding_record.question_uuid} not found in CodingQuestionBank")
                        continue
                    
                    # Get difficulty (from question or coding_record)
                    difficulty = (question.difficulty or coding_record.difficulty or "medium").lower()
                    difficulty_weight = DIFFICULTY_SCORES.get(difficulty, 1)
                    
                    # Calculate max possible score for this question
                    # Count sample_test_cases and test_cases
                    sample_test_cases = question.sample_test_cases
                    test_cases = question.test_cases
                    
                    num_sample = len(sample_test_cases) if isinstance(sample_test_cases, list) else 0
                    num_hidden = len(test_cases) if isinstance(test_cases, list) else 0
                    
                    max_base_score = (num_sample * 5) + (num_hidden * 10)
                    max_weighted_score = max_base_score * difficulty_weight
                    
                    # Add max score to total (for all assigned questions)
                    total_weighted_max_score += max_weighted_score
                    
                    # Only process actual scores for submitted questions
                    if coding_record.score is not None:
                        # Get actual score from submission
                        actual_score = coding_record.score or 0
                        actual_weighted_score = actual_score * difficulty_weight
                        
                        # Add to totals
                        total_weighted_actual_score += actual_weighted_score
                        
                        # Get total test cases for this question
                        total_test_cases = num_sample + num_hidden
                        test_cases_passed = coding_record.test_cases_passed or 0
                        
                        # Check if correct or partially correct
                        if test_cases_passed == total_test_cases and total_test_cases > 0:
                            total_correct += 1
                        elif 0 < test_cases_passed < total_test_cases:
                            partially_correct += 1
                
                # Calculate normalized score (0-100)
                if total_weighted_max_score > 0:
                    normalized_score = round((total_weighted_actual_score / total_weighted_max_score) * 100, 2)
                else:
                    normalized_score = 0.0
                
                # Build coding analysis JSON
                coding_analysis = {
                    "total_score": float(normalized_score),
                    "time_taken": 0,  # Will be set below
                    "total_submitted": int(total_submitted),
                    "total_correct": int(total_correct),
                    "partially_correct": int(partially_correct)
                }
            
            # Get time taken from test_session
            candidate = self.db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            time_taken = 0
            if candidate and candidate.test_session and candidate.test_session.section_timings:
                section_timings = candidate.test_session.section_timings
                if isinstance(section_timings, dict) and "coding" in section_timings:
                    coding_timing = section_timings["coding"]
                    if isinstance(coding_timing, dict) and "duration_seconds" in coding_timing:
                        time_taken = coding_timing["duration_seconds"]
                    # If duration_seconds not available, calculate from started_at
                    elif isinstance(coding_timing, dict) and "started_at" in coding_timing:
                        try:
                            started_at_str = coding_timing["started_at"]
                            started_at = datetime.fromisoformat(started_at_str)
                            time_taken = int((datetime.utcnow() - started_at).total_seconds())
                        except Exception as e:
                            logger.warning(f"Failed to calculate time_taken from started_at: {str(e)}")
            
            # Update time_taken in analysis
            coding_analysis["time_taken"] = int(time_taken)
            
            # Get or create interview_analysis record
            interview_analysis = self.db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if interview_analysis:
                # Update existing record
                interview_analysis.coding_analysis = coding_analysis
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Updated coding_analysis for candidate {candidate_id}")
            else:
                # Create new record
                interview_analysis = InterviewAnalysisTable(
                    candidate_id=candidate_id,
                    coding_analysis=coding_analysis
                )
                self.db.add(interview_analysis)
                logger.info(f"[INTERVIEW_ANALYSIS] ✅ Created new interview_analysis record with coding_analysis for candidate {candidate_id}")
            
            # Commit the analysis update
            self.db.commit()
            
            # Try to send assessment report email if all analyses are ready
            try:
                import threading
                import asyncio
                from services.email_service import email_service
                
                def try_send_email_async():
                    """Helper function to run async email sending in background thread."""
                    try:
                        # Create a new database session for the email thread
                        from core.database import get_db
                        db_gen = get_db()
                        db_email = next(db_gen)
                        try:
                            asyncio.run(
                                email_service.try_send_assessment_report_email_if_ready(
                                    candidate_id=candidate_id,
                                    db=db_email
                                )
                            )
                        finally:
                            db_email.close()
                    except Exception as e:
                        logger.error(f"Error in background email thread for candidate {candidate_id}: {str(e)}", exc_info=True)
                
                # Start email check in background thread (non-blocking)
                email_thread = threading.Thread(target=try_send_email_async, daemon=True)
                email_thread.start()
                logger.info(f"Triggered email check for candidate {candidate_id} after coding analysis update")
            except Exception as e:
                # Don't fail if email trigger fails
                logger.warning(f"Failed to trigger email check for candidate {candidate_id}: {str(e)}")
            
        except Exception as e:
            logger.error(f"Error updating coding analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
            # Don't raise - let the calling method handle it
            raise
    
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
            interview_analysis = self.db.query(InterviewAnalysisTable).filter(
                InterviewAnalysisTable.candidate_id == candidate_id
            ).first()
            
            if not interview_analysis:
                logger.warning(f"No interview analysis found for candidate {candidate_id}, cannot generate summary")
                return
            
            # Extract MCQ metadata
            mcq_analysis = interview_analysis.mcq_analysis or {}
            mcq_metadata = {
                "score": mcq_analysis.get("score", 0),
                "time_taken": mcq_analysis.get("time_taken", 0),
                "attempted": mcq_analysis.get("attempted", {"easy": 0, "medium": 0, "hard": 0}),
                "correct": mcq_analysis.get("correct", {"easy": 0, "medium": 0, "hard": 0})
            }
            
            # Extract Coding metadata
            coding_analysis = interview_analysis.coding_analysis or {}
            coding_metadata = {
                "total_score": coding_analysis.get("total_score", 0),
                "time_taken": coding_analysis.get("time_taken", 0),
                "total_submitted": coding_analysis.get("total_submitted", 0),
                "total_correct": coding_analysis.get("total_correct", 0),
                "partially_correct": coding_analysis.get("partially_correct", 0)
            }
            
            # Extract System Design metadata
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
            
            # Import and call the summary generator
            from utils.analysis_summary import generate_interview_summary
            
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
    
    def ensure_all_analyses_complete(self, candidate_id: str) -> Dict[str, Any]:
        """
        Ensure all section analyses are complete before test completion.
        Performs analysis for any missing sections.
        
        This method intelligently checks each section (MCQ, Coding, System Design)
        and only performs analysis if it doesn't already exist, preventing duplicates.
        
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
        from models.interview_analysis_table import InterviewAnalysisTable
        from models.interview_coding import InterviewCoding
        from models.interview_system_design import InterviewSystemDesign
        
        completed = []
        skipped = []
        failed = []
        
        # Get or create interview_analysis record
        interview_analysis = self.db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if not interview_analysis:
            interview_analysis = InterviewAnalysisTable(candidate_id=candidate_id)
            self.db.add(interview_analysis)
            self.db.flush()
            logger.info(f"[ENSURE_ANALYSIS] Created new interview_analysis record for candidate {candidate_id}")
        
        # ============================================================================
        # 1. MCQ Analysis
        # ============================================================================
        if not interview_analysis.mcq_analysis or interview_analysis.mcq_analysis.get("score") is None:
            try:
                self._update_mcq_analysis(candidate_id)
                completed.append("mcq")
                logger.info(f"[ENSURE_ANALYSIS] ✅ Completed MCQ analysis for {candidate_id}")
            except Exception as e:
                failed.append(("mcq", str(e)))
                logger.error(f"[ENSURE_ANALYSIS] ❌ Failed MCQ analysis: {e}")
        else:
            skipped.append("mcq")
            logger.info(f"[ENSURE_ANALYSIS] ⏭️  MCQ analysis already exists for {candidate_id}")
        
        # ============================================================================
        # 2. Coding Analysis
        # ============================================================================
        self.db.refresh(interview_analysis)
        if not interview_analysis.coding_analysis or interview_analysis.coding_analysis.get("total_score") is None:
            # Check if candidate has coding questions
            has_coding = self.db.query(InterviewCoding).filter(
                InterviewCoding.candidate_id == candidate_id
            ).first() is not None
            
            if has_coding:
                try:
                    self._update_coding_analysis(candidate_id)
                    completed.append("coding")
                    logger.info(f"[ENSURE_ANALYSIS] ✅ Completed Coding analysis for {candidate_id}")
                except Exception as e:
                    failed.append(("coding", str(e)))
                    logger.error(f"[ENSURE_ANALYSIS] ❌ Failed Coding analysis: {e}")
            else:
                skipped.append("coding_no_questions")
                logger.info(f"[ENSURE_ANALYSIS] ⏭️  No coding questions assigned for {candidate_id}")
        else:
            skipped.append("coding")
            logger.info(f"[ENSURE_ANALYSIS] ⏭️  Coding analysis already exists for {candidate_id}")
        
        # ============================================================================
        # 3. System Design Analysis
        # ============================================================================
        self.db.refresh(interview_analysis)
        if not interview_analysis.system_design_analysis or interview_analysis.system_design_analysis.get("score") is None:
            # Check if candidate has system design session
            sd_record = self.db.query(InterviewSystemDesign).filter(
                InterviewSystemDesign.candidate_id == candidate_id
            ).first()
            
            if sd_record and (sd_record.current_canvas or sd_record.final_diagram):
                try:
                    from services.system_design_service import SystemDesignService
                    import asyncio
                    
                    sd_service = SystemDesignService(self.db)
                    asyncio.run(
                        sd_service.generate_final_report(
                            candidate_id=candidate_id,
                            question_uuid=sd_record.question_uuid
                        )
                    )
                    completed.append("system_design")
                    logger.info(f"[ENSURE_ANALYSIS] ✅ Completed System Design analysis for {candidate_id}")
                except Exception as e:
                    failed.append(("system_design", str(e)))
                    logger.error(f"[ENSURE_ANALYSIS] ❌ Failed System Design analysis: {e}")
            else:
                skipped.append("system_design_no_session")
                logger.info(f"[ENSURE_ANALYSIS] ⏭️  No system design session or canvas data for {candidate_id}")
        else:
            skipped.append("system_design")
            logger.info(f"[ENSURE_ANALYSIS] ⏭️  System Design analysis already exists for {candidate_id}")
        
        return {
            "success": len(failed) == 0,
            "completed_analyses": completed,
            "skipped_analyses": skipped,
            "failed_analyses": failed
        }
    
    async def _assign_questions_and_generate_mcq(self, candidate_id: str, candidate: Candidate, scheduled_date_for_message: datetime) -> tuple:
        """
        Helper function to assign questions and generate MCQ questions.
        Shared logic between schedule-based and immediate start flows.
        
        Args:
            candidate_id: UUID of the candidate
            candidate: Candidate object
            scheduled_date_for_message: datetime to use in response message
            
        Returns:
            Tuple of (error_messages list, system_design_result, mcq_result, coding_result)
        """
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
        # Parallel tasks: System Design Question Assignment, MCQ Generation, and Coding Question Assignment
        system_design_result = None
        mcq_result = None
        coding_result = None
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
        
        # Task 2: Assign coding questions to candidate
        try:
            from services.coding_question_assignment_service import CodingQuestionAssignmentService
            from core.config import settings
            coding_service = CodingQuestionAssignmentService(self.db)
            coding_result = coding_service.assign_coding_questions_to_candidate(
                candidate_id=candidate_id,
                use_random=settings.RANDOM_CODING_QUESTIONS
            )
            if not coding_result.get("success"):
                error_messages.append(f"Coding question assignment failed: {coding_result.get('message', 'Unknown error')}")
        except Exception as e:
            error_messages.append(f"Coding question assignment error: {str(e)}")
        
        # Task 3: Generate and save MCQ questions (if resume and job description are available)
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
                generation_result = await mcq_service.generate_questions(mcq_request)
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
            
            # Send test invitation email and calendar invites AUTOMATICALLY after questions are generated and assigned
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
                                    
                                    # 2. Send candidate calendar invite (requires db session for OAuth token lookup)
                                    calendar_task = calendar_service.create_candidate_calendar_event(
                                        candidate_email=candidate.email_id,
                                        candidate_name=candidate.name,
                                        job_role=job_role,
                                        test_link=test_link,
                                        scheduled_date=request.scheduled_date,
                                        db=db_session  # Pass database session for OAuth token lookup
                                    )
                                    
                                    # 3. Send recruiter email (if recruiter exists)
                                    recruiter_email_task = None
                                    recruiter_calendar_task = None
                                    
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
                                        
                                        # 4. Send recruiter calendar invite (requires db session)
                                        recruiter_calendar_task = calendar_service.create_recruiter_calendar_event(
                                            recruiter_email=recruiter.email_id,
                                            recruiter_name=recruiter.name,
                                            candidate_name=candidate.name,
                                            candidate_email=candidate.email_id,
                                            candidate_reference_number=candidate.candidate_reference_number,
                                            job_role=job_role,
                                            scheduled_date=request.scheduled_date,
                                            db=db_session  # Pass database session for OAuth token lookup
                                        )
                                    
                                    # Wait for all tasks to complete
                                    tasks = [email_task, calendar_task]
                                    if recruiter_email_task:
                                        tasks.append(recruiter_email_task)
                                    if recruiter_calendar_task:
                                        tasks.append(recruiter_calendar_task)
                                    
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
                    
                    logger.info(f"Test invitation notifications (email + calendar) queued for candidate {candidate_id} and recruiter after questions were assigned")
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
            
            # Send test invitation email and calendar invites AUTOMATICALLY after questions are generated and assigned
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
                                    
                                    # 2. Send candidate calendar invite (requires db session for OAuth token lookup)
                                    calendar_task = calendar_service.create_candidate_calendar_event(
                                        candidate_email=candidate.email_id,
                                        candidate_name=candidate.name,
                                        job_role=job_role,
                                        test_link=test_link,
                                        scheduled_date=request.scheduled_date,
                                        db=db_session  # Pass database session for OAuth token lookup
                                    )
                                    
                                    # 3. Send recruiter email (if recruiter exists)
                                    recruiter_email_task = None
                                    recruiter_calendar_task = None
                                    
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
                                        
                                        # 4. Send recruiter calendar invite (requires db session)
                                        recruiter_calendar_task = calendar_service.create_recruiter_calendar_event(
                                            recruiter_email=recruiter.email_id,
                                            recruiter_name=recruiter.name,
                                            candidate_name=candidate.name,
                                            candidate_email=candidate.email_id,
                                            candidate_reference_number=candidate.candidate_reference_number,
                                            job_role=job_role,
                                            scheduled_date=request.scheduled_date,
                                            db=db_session  # Pass database session for OAuth token lookup
                                        )
                                    
                                    # Wait for all tasks to complete
                                    tasks = [email_task, calendar_task]
                                    if recruiter_email_task:
                                        tasks.append(recruiter_email_task)
                                    if recruiter_calendar_task:
                                        tasks.append(recruiter_calendar_task)
                                    
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
                    
                    logger.info(f"Test invitation notifications (email + calendar) queued for candidate {candidate_id} and recruiter after questions were assigned")
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

