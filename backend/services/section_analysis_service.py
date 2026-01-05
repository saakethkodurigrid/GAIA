"""
Section Analysis Service - Standalone analysis functions for background execution.

These functions contain pure analysis + persistence logic and are safe to call
from background jobs. They accept only candidate_id and db session, with no
dependencies on request/session/API context.
"""
import logging
import asyncio
from typing import Dict, Any, Optional, Callable
from sqlalchemy.orm import Session
from models.interview_mcq import InterviewMCQ
from models.interview_coding import InterviewCoding
from models.coding_question_bank import CodingQuestionBank
from models.interview_analysis_table import InterviewAnalysisTable
from models.interview_system_design import InterviewSystemDesign
from datetime import datetime
from schemas.analysis import SectionType, AnalysisStatus

logger = logging.getLogger(__name__)


def _persist_system_design_analysis(
    candidate_id: str,
    final_report: Dict[str, Any],
    db: Session,
    extract_strengths_fn: Callable[[str, Dict[str, float]], Dict[str, list]],
    evaluation: Optional[Dict[str, Any]] = None
) -> None:
    """
    Helper function to persist system design analysis to interview_analysis_table.
    
    This is the core persistence logic extracted for reuse by both
    _save_to_interview_analysis_table and analyze_system_design.
    
    Args:
        candidate_id: UUID of the candidate
        final_report: Final report dictionary with analysis data
        db: Database session
        extract_strengths_fn: Function to extract strengths and improvements from feedback
        evaluation: Optional evaluation dictionary with scores and feedback
    """
    # Extract data from final_report
    avg_scores = final_report.get("average_scores", {})
    
    # Calculate overall score (0-100) from average scores with non-linear conversion
    if avg_scores:
        avg_score = sum(avg_scores.values()) / len(avg_scores)
        # Non-linear conversion: more harsh for incomplete designs, fair for complete ones
        if avg_score <= 2.5:
            # Incomplete designs: harsher conversion (1.8 → 27 instead of 36)
            overall_score = int(round(avg_score * 15))
        elif avg_score <= 3.5:
            # Standard conversion for mid-range scores
            overall_score = int(round(avg_score * 20))
        else:
            # High scores: slight bonus (4.5 → 99 instead of 90)
            overall_score = int(round(avg_score * 22))
        # Clamp to 0-100 range
        overall_score = max(0, min(100, overall_score))
    else:
        overall_score = None
    
    # Extract strengths and improvements
    feedback = evaluation.get("feedback", "") if evaluation else final_report.get("final_feedback", "")
    extraction = extract_strengths_fn(feedback, avg_scores)
    
    # Build system_design_analysis JSONB object
    system_design_analysis = {
        "score": overall_score,
        "key_strengths": extraction["key_strengths"],
        "things_to_improve": extraction["things_to_improve"],
        "summary": final_report.get("final_feedback", ""),
        "average_scores": avg_scores,  # Store detailed scores too
        "lowest_area": final_report.get("lowest_area"),
        "suggested_learning": final_report.get("suggested_learning", [])
    }
    
    # Get or create interview_analysis record
    interview_analysis = db.query(InterviewAnalysisTable).filter(
        InterviewAnalysisTable.candidate_id == candidate_id
    ).first()
    
    if interview_analysis:
        # Update existing record
        interview_analysis.system_design_analysis = system_design_analysis
        logger.info(f"[INTERVIEW_ANALYSIS] ✅ Updated system_design_analysis for candidate {candidate_id}")
    else:
        # Create new record
        interview_analysis = InterviewAnalysisTable(
            candidate_id=candidate_id,
            system_design_analysis=system_design_analysis
        )
        db.add(interview_analysis)
        logger.info(f"[INTERVIEW_ANALYSIS] ✅ Created new interview_analysis record for candidate {candidate_id}")
    
    db.commit()


def analyze_mcq(candidate_id: str, db: Session) -> None:
    """
    Analyze MCQ section and persist results to interview_analysis_table.
    
    Fully self-contained function that:
    a. Checks if questions are assigned - if not, writes ZERO analysis JSON
    b. Checks if any answers exist - if not, writes ZERO analysis JSON
    c. Otherwise computes score and persists analysis JSON
    
    Never leaves analysis JSON as null.
    
    This function is safe to call from background jobs as it has no
    dependencies on request/session/API context.
    
    Idempotent: Uses AnalysisStatusService to check if already completed.
    
    Args:
        candidate_id: UUID of the candidate
        db: Database session
    """
    from services.analysis_status_service import AnalysisStatusService
    from schemas.analysis import SectionType, AnalysisStatus as AnalysisStatusEnum
    
    # Check analysis status for idempotency
    status_service = AnalysisStatusService(db)
    current_status = status_service.get_status(candidate_id, SectionType.MCQ)
    
    if current_status:
        # If already completed, exit immediately (idempotent)
        if current_status.status == AnalysisStatusEnum.COMPLETED.value:
            logger.info(f"MCQ analysis already completed for candidate {candidate_id}, skipping")
            return
        
        # If not in progress, exit defensively (another process may be working on it)
        if current_status.status != AnalysisStatusEnum.IN_PROGRESS.value:
            logger.warning(
                f"MCQ analysis for candidate {candidate_id} is in state {current_status.status}, "
                f"expected IN_PROGRESS. Skipping analysis."
            )
            return
    else:
        # No status record exists - this shouldn't happen if properly initialized
        # but we'll be defensive and exit
        logger.warning(f"No analysis status found for MCQ section for candidate {candidate_id}, skipping")
        return
    
    try:
        # Define difficulty scoring weights
        DIFFICULTY_SCORES = {
            "hard": 3,
            "medium": 2,
            "easy": 1
        }
        
        # Step a: Check if questions are assigned for the section
        logger.info(f"[DATA_SOURCE] 📊 Fetching MCQ questions from POSTGRESQL for candidate {candidate_id}")
        all_mcqs = db.query(InterviewMCQ).filter(
            InterviewMCQ.candidate_id == candidate_id
        ).all()
        
        logger.info(f"[DATA_SOURCE] ✅ Found {len(all_mcqs)} MCQ questions in POSTGRESQL for candidate {candidate_id}")
        
        if not all_mcqs:
            # No questions assigned - write ZERO analysis JSON
            mcq_analysis = {
                "total_questions": 0,
                "attempted": {"easy": 0, "medium": 0, "hard": 0},
                "correct": {"easy": 0, "medium": 0, "hard": 0},
                "score": 0,
                "percentage": 0
            }
        else:
            # Step b: Check if any answers exist
            has_answers = any(mcq.candidate_answer is not None for mcq in all_mcqs)
            
            if not has_answers:
                # No answers submitted - write ZERO analysis JSON
                mcq_analysis = {
                    "total_questions": len(all_mcqs),
                    "attempted": {"easy": 0, "medium": 0, "hard": 0},
                    "correct": {"easy": 0, "medium": 0, "hard": 0},
                    "score": 0,
                    "percentage": 0
                }
            else:
                # Step c: Compute score and build analysis JSON
                attempted = {"easy": 0, "medium": 0, "hard": 0}
                correct = {"easy": 0, "medium": 0, "hard": 0}
                total_score = 0
                max_possible_score = 0
                total_attempted = 0
                total_correct = 0
                
                # Calculate scores and counts
                for mcq in all_mcqs:
                    difficulty = (mcq.difficulty or "medium").lower()
                    difficulty_score = DIFFICULTY_SCORES.get(difficulty, 1)
                    
                    # Add to max possible score (all questions)
                    max_possible_score += difficulty_score
                    
                    # Check if question was attempted
                    if mcq.candidate_answer is not None:
                        total_attempted += 1
                        attempted[difficulty] = attempted.get(difficulty, 0) + 1
                        
                        # Check if answer is correct
                        if mcq.candidate_answer == mcq.correct_answer:
                            total_score += difficulty_score
                            total_correct += 1
                            correct[difficulty] = correct.get(difficulty, 0) + 1
                
                # Calculate normalized score (0-100)
                if max_possible_score > 0:
                    normalized_score = round((total_score / max_possible_score) * 100, 2)
                else:
                    normalized_score = 0.0
                
                # Build MCQ analysis JSON
                mcq_analysis = {
                    "total_questions": len(all_mcqs),
                    "attempted": attempted,
                    "correct": correct,
                    "score": float(normalized_score),
                    "percentage": float(normalized_score)
                }
        
        # Get or create interview_analysis record
        logger.info(f"[DATA_SOURCE] 💾 Saving MCQ analysis to POSTGRESQL (InterviewAnalysisTable) for candidate {candidate_id}")
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if interview_analysis:
            # Update existing record
            interview_analysis.mcq_analysis = mcq_analysis
            logger.info(f"[DATA_SOURCE] ✅ Updated mcq_analysis in POSTGRESQL for candidate {candidate_id}")
        else:
            # Create new record
            interview_analysis = InterviewAnalysisTable(
                candidate_id=candidate_id,
                mcq_analysis=mcq_analysis
            )
            db.add(interview_analysis)
            logger.info(f"[DATA_SOURCE] ✅ Created new interview_analysis record with mcq_analysis in POSTGRESQL for candidate {candidate_id}")
        
        # Commit the analysis update
        db.commit()
        logger.info(f"[DATA_SOURCE] ✅ Committed MCQ analysis to POSTGRESQL for candidate {candidate_id}")
        
        # Mark analysis as completed
        status_service.mark_completed(candidate_id, SectionType.MCQ)
        logger.info(f"[ANALYSIS_STATUS] ✅ Marked MCQ analysis as COMPLETED for candidate {candidate_id}")
        
        # Emit completion event
        from services.analysis_events import on_section_analysis_completed
        on_section_analysis_completed(candidate_id, SectionType.MCQ)

    except Exception as e:
        logger.error(f"Error analyzing MCQ for candidate {candidate_id}: {str(e)}", exc_info=True)
        db.rollback()
        
        # Mark analysis as failed
        try:
            status_service.mark_failed(candidate_id, SectionType.MCQ)
            logger.info(f"[ANALYSIS_STATUS] ❌ Marked MCQ analysis as FAILED for candidate {candidate_id}")
        except Exception as status_error:
            logger.error(f"Failed to mark MCQ analysis as failed: {str(status_error)}")
        
        raise


def analyze_coding(candidate_id: str, db: Session) -> None:
    """
    Analyze coding section and persist results to interview_analysis_table.
    
    Fully self-contained function that:
    a. Checks if questions are assigned - if not, writes ZERO analysis JSON
    b. Checks if any submissions exist - if not, writes ZERO analysis JSON
    c. Otherwise computes score and persists analysis JSON
    
    Never leaves analysis JSON as null.
    
    This function is safe to call from background jobs as it has no
    dependencies on request/session/API context.
    
    Idempotent: Uses AnalysisStatusService to check if already completed.
    
    Args:
        candidate_id: UUID of the candidate
        db: Database session
    """
    from services.analysis_status_service import AnalysisStatusService
    from schemas.analysis import SectionType, AnalysisStatus as AnalysisStatusEnum
    
    # Check analysis status for idempotency
    status_service = AnalysisStatusService(db)
    current_status = status_service.get_status(candidate_id, SectionType.CODING)
    
    if current_status:
        # If already completed, exit immediately (idempotent)
        if current_status.status == AnalysisStatusEnum.COMPLETED.value:
            logger.info(f"Coding analysis already completed for candidate {candidate_id}, skipping")
            return
        
        # If not in progress, exit defensively (another process may be working on it)
        if current_status.status != AnalysisStatusEnum.IN_PROGRESS.value:
            logger.warning(
                f"Coding analysis for candidate {candidate_id} is in state {current_status.status}, "
                f"expected IN_PROGRESS. Skipping analysis."
            )
            return
    else:
        # No status record exists - this shouldn't happen if properly initialized
        # but we'll be defensive and exit
        logger.warning(f"No analysis status found for Coding section for candidate {candidate_id}, skipping")
        return
    
    try:
        # Step a: Check if questions are assigned for the section
        logger.info(f"[DATA_SOURCE] 📊 Fetching coding questions from POSTGRESQL for candidate {candidate_id}")
        all_coding_records = db.query(InterviewCoding).filter(
            InterviewCoding.candidate_id == candidate_id
        ).all()
        
        logger.info(f"[DATA_SOURCE] ✅ Found {len(all_coding_records)} coding questions in POSTGRESQL for candidate {candidate_id}")
        
        if not all_coding_records:
            # No questions assigned - write ZERO analysis JSON
            coding_analysis = {
                "total_questions": 0,
                "attempted": 0,
                "passed": 0,
                "total_score": 0
            }
        else:
            # Step b: Check if any submissions exist (score is not None)
            has_submissions = any(record.score is not None for record in all_coding_records)
            
            if not has_submissions:
                # No submissions - write ZERO analysis JSON
                coding_analysis = {
                    "total_questions": len(all_coding_records),
                    "attempted": 0,
                    "passed": 0,
                    "total_score": 0
                }
            else:
                # Step c: Compute score and build analysis JSON
                # Define difficulty scoring weights
                DIFFICULTY_SCORES = {
                    "hard": 3,
                    "medium": 2,
                    "easy": 1
                }
                
                total_attempted = 0
                total_passed = 0
                total_weighted_actual_score = 0
                total_weighted_max_score = 0
                
                # Process all assigned questions
                for coding_record in all_coding_records:
                    # Get question details from CodingQuestionBank
                    question = db.query(CodingQuestionBank).filter(
                        CodingQuestionBank.uuid == coding_record.question_uuid
                    ).first()
                    
                    if not question:
                        logger.warning(f"Question {coding_record.question_uuid} not found in CodingQuestionBank")
                        continue
                    
                    # Get difficulty
                    difficulty = (question.difficulty or coding_record.difficulty or "medium").lower()
                    difficulty_weight = DIFFICULTY_SCORES.get(difficulty, 1)
                    
                    # Calculate max possible score for this question
                    sample_test_cases = question.sample_test_cases
                    test_cases = question.test_cases
                    
                    num_sample = len(sample_test_cases) if isinstance(sample_test_cases, list) else 0
                    num_hidden = len(test_cases) if isinstance(test_cases, list) else 0
                    
                    max_base_score = (num_sample * 5) + (num_hidden * 10)
                    max_weighted_score = max_base_score * difficulty_weight
                    total_weighted_max_score += max_weighted_score
                    
                    # Process actual scores for submitted questions
                    if coding_record.score is not None:
                        total_attempted += 1
                        actual_score = coding_record.score or 0
                        actual_weighted_score = actual_score * difficulty_weight
                        total_weighted_actual_score += actual_weighted_score
                        
                        # Check if all test cases passed
                        total_test_cases = num_sample + num_hidden
                        test_cases_passed = coding_record.test_cases_passed or 0
                        if test_cases_passed == total_test_cases and total_test_cases > 0:
                            total_passed += 1
                
                # Calculate normalized score (0-100)
                if total_weighted_max_score > 0:
                    normalized_score = round((total_weighted_actual_score / total_weighted_max_score) * 100, 2)
                else:
                    normalized_score = 0.0
                
                # Build coding analysis JSON
                coding_analysis = {
                    "total_questions": len(all_coding_records),
                    "attempted": total_attempted,
                    "passed": total_passed,
                    "total_score": float(normalized_score)
                }
        
        # Get or create interview_analysis record
        logger.info(f"[DATA_SOURCE] 💾 Saving coding analysis to POSTGRESQL (InterviewAnalysisTable) for candidate {candidate_id}")
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if interview_analysis:
            # Update existing record
            interview_analysis.coding_analysis = coding_analysis
            logger.info(f"[DATA_SOURCE] ✅ Updated coding_analysis in POSTGRESQL for candidate {candidate_id}")
        else:
            # Create new record
            interview_analysis = InterviewAnalysisTable(
                candidate_id=candidate_id,
                coding_analysis=coding_analysis
            )
            db.add(interview_analysis)
            logger.info(f"[DATA_SOURCE] ✅ Created new interview_analysis record with coding_analysis in POSTGRESQL for candidate {candidate_id}")
        
        # Commit the analysis update
        db.commit()
        logger.info(f"[DATA_SOURCE] ✅ Committed coding analysis to POSTGRESQL for candidate {candidate_id}")
        
        # Mark analysis as completed
        status_service.mark_completed(candidate_id, SectionType.CODING)
        logger.info(f"[ANALYSIS_STATUS] ✅ Marked Coding analysis as COMPLETED for candidate {candidate_id}")
        
        # Emit completion event
        from services.analysis_events import on_section_analysis_completed
        on_section_analysis_completed(candidate_id, SectionType.CODING)

    except Exception as e:
        logger.error(f"Error analyzing coding for candidate {candidate_id}: {str(e)}", exc_info=True)
        db.rollback()
        
        # Mark analysis as failed
        try:
            status_service.mark_failed(candidate_id, SectionType.CODING)
            logger.info(f"[ANALYSIS_STATUS] ❌ Marked Coding analysis as FAILED for candidate {candidate_id}")
        except Exception as status_error:
            logger.error(f"Failed to mark Coding analysis as failed: {str(status_error)}")
        
        raise


def analyze_system_design(candidate_id: str, db: Session) -> None:
    """
    Analyze system design section and persist results to interview_analysis_table.
    
    This function:
    1. Fetches system design records for the candidate
    2. For each submitted design, generates final report and evaluation
    3. Persists the analysis to interview_analysis_table
    
    This function is safe to call from background jobs as it has no
    dependencies on request/session/API context. However, it does need
    to reconstruct session data from database/Redis to generate reports.
    
    Idempotent: Uses AnalysisStatusService to check if already completed.
    
    Args:
        candidate_id: UUID of the candidate
        db: Database session
    """
    from services.analysis_status_service import AnalysisStatusService
    from schemas.analysis import SectionType, AnalysisStatus as AnalysisStatusEnum
    
    # Check analysis status for idempotency
    status_service = AnalysisStatusService(db)
    current_status = status_service.get_status(candidate_id, SectionType.SYSTEM_DESIGN)
    
    if current_status:
        # If already completed, exit immediately (idempotent)
        if current_status.status == AnalysisStatusEnum.COMPLETED.value:
            logger.info(f"System Design analysis already completed for candidate {candidate_id}, skipping")
            return
        
        # If not in progress, exit defensively (another process may be working on it)
        if current_status.status != AnalysisStatusEnum.IN_PROGRESS.value:
            logger.warning(
                f"System Design analysis for candidate {candidate_id} is in state {current_status.status}, "
                f"expected IN_PROGRESS. Skipping analysis."
            )
            return
    else:
        # No status record exists - this shouldn't happen if properly initialized
        # but we'll be defensive and exit
        logger.warning(f"No analysis status found for System Design section for candidate {candidate_id}, skipping")
        return
    
    try:
        # Get system design records for this candidate
        sd_records = db.query(InterviewSystemDesign).filter(
            InterviewSystemDesign.candidate_id == candidate_id
        ).all()
        
        if not sd_records:
            # No system design questions assigned - write ZERO analysis JSON
            fallback_report = {
                "average_scores": {},
                "final_feedback": "No system design submission",
                "lowest_area": None,
                "suggested_learning": []
            }
            from services.system_design_service import SystemDesignService
            sd_service = SystemDesignService(db)
            _persist_system_design_analysis(
                candidate_id=candidate_id,
                final_report=fallback_report,
                evaluation=None,
                db=db,
                extract_strengths_fn=sd_service._extract_strengths_and_improvements_simple
            )
            logger.info(f"[DATA_SOURCE] ✅ Saved zero system_design_analysis for candidate {candidate_id}")
            
            # Mark analysis as completed
            status_service.mark_completed(candidate_id, SectionType.SYSTEM_DESIGN)
            logger.info(f"[ANALYSIS_STATUS] ✅ Marked System Design analysis as COMPLETED for candidate {candidate_id}")
            
            # Emit completion event
            from services.analysis_events import on_section_analysis_completed
            on_section_analysis_completed(candidate_id, SectionType.SYSTEM_DESIGN)
            return
        
        # Find the first submitted/evaluated record (typically there's one per candidate)
        submitted_record = None
        for record in sd_records:
            if record.status in ('submitted', 'evaluated') or record.score is not None:
                submitted_record = record
                break
        
        # If no submitted record, check for any record with canvas data
        if not submitted_record:
            for record in sd_records:
                if record.current_canvas or record.diagram:
                    submitted_record = record
                    break
        
        if not submitted_record:
            # No submission - write ZERO analysis JSON
            fallback_report = {
                "average_scores": {},
                "final_feedback": "No system design submission",
                "lowest_area": None,
                "suggested_learning": []
            }
            from services.system_design_service import SystemDesignService
            sd_service = SystemDesignService(db)
            _persist_system_design_analysis(
                candidate_id=candidate_id,
                final_report=fallback_report,
                evaluation=None,
                db=db,
                extract_strengths_fn=sd_service._extract_strengths_and_improvements_simple
            )
            logger.info(f"[DATA_SOURCE] ✅ Saved zero system_design_analysis for candidate {candidate_id}")
            
            # Mark analysis as completed
            status_service.mark_completed(candidate_id, SectionType.SYSTEM_DESIGN)
            logger.info(f"[ANALYSIS_STATUS] ✅ Marked System Design analysis as COMPLETED for candidate {candidate_id}")
            
            # Emit completion event
            from services.analysis_events import on_section_analysis_completed
            on_section_analysis_completed(candidate_id, SectionType.SYSTEM_DESIGN)
            return
        
        # Process submitted record
        try:
            # Generate final report and evaluation for the submitted design
            # Import here to avoid circular dependencies
            from services.system_design_service import SystemDesignService
            import asyncio
            
            sd_service = SystemDesignService(db)
            question_uuid = submitted_record.question_uuid
            
            # Generate final report (this will also save to interview_analysis_table)
            # But we need to handle it properly - generate_final_report expects a session
            # We'll need to get the session from Redis or reconstruct it
            
            try:
                # Try to get session from Redis first (fastest)
                session = sd_service.get_session(candidate_id, question_uuid)
                
                # Generate final report
                report = asyncio.run(
                    sd_service.evaluator.generate_final_report(
                        session,
                        evaluation_criteria=None,  # Will be fetched inside if needed
                        evaluation_context=None
                    )
                )
                
                # Get the latest evaluation for extracting strengths/improvements
                latest_evaluation = None
                if session.evaluations:
                    latest_evaluation = {
                        "scores": session.evaluations[-1].scores,
                        "feedback": session.evaluations[-1].feedback,
                        "follow_up": session.evaluations[-1].follow_up
                    }
                elif report.get("timeline"):
                    # Extract from timeline if available
                    latest_timeline_item = report.get("timeline", [])[-1] if report.get("timeline") else None
                    if latest_timeline_item:
                        latest_evaluation = {
                            "scores": latest_timeline_item.get("scores", {}),
                            "feedback": latest_timeline_item.get("feedback", ""),
                            "follow_up": latest_timeline_item.get("follow_up", "")
                        }
                
                # Extract data from final_report
                avg_scores = report.get("average_scores", {})
                
                # Calculate overall score (0-100) from average scores with non-linear conversion
                if avg_scores:
                    avg_score = sum(avg_scores.values()) / len(avg_scores)
                    # Non-linear conversion: more harsh for incomplete designs, fair for complete ones
                    if avg_score <= 2.5:
                        # Incomplete designs: harsher conversion (1.8 → 27 instead of 36)
                        overall_score = int(round(avg_score * 15))
                    elif avg_score <= 3.5:
                        # Standard conversion for mid-range scores
                        overall_score = int(round(avg_score * 20))
                    else:
                        # High scores: slight bonus (4.5 → 99 instead of 90)
                        overall_score = int(round(avg_score * 22))
                    # Clamp to 0-100 range
                    overall_score = max(0, min(100, overall_score))
                else:
                    overall_score = submitted_record.score  # Use score from DB if available
                
                # Use helper function to persist analysis
                _persist_system_design_analysis(
                    candidate_id=candidate_id,
                    final_report=report,
                    evaluation=latest_evaluation,
                    db=db,
                    extract_strengths_fn=sd_service._extract_strengths_and_improvements_simple
                )
                logger.info(f"[DATA_SOURCE] ✅ Committed system design analysis to POSTGRESQL for candidate {candidate_id}")
                
                # Mark analysis as completed
                status_service.mark_completed(candidate_id, SectionType.SYSTEM_DESIGN)
                logger.info(f"[ANALYSIS_STATUS] ✅ Marked System Design analysis as COMPLETED for candidate {candidate_id}")
                
                # Emit completion event
                from services.analysis_events import on_section_analysis_completed
                on_section_analysis_completed(candidate_id, SectionType.SYSTEM_DESIGN)
                return
                
            except Exception as e:
                logger.warning(f"Failed to generate full report for system design analysis: {str(e)}")
                # Fallback: use data from database record
                fallback_report = {
                    "average_scores": {},
                    "final_feedback": "System design submitted but detailed analysis unavailable",
                    "lowest_area": None,
                    "suggested_learning": []
                }
                fallback_evaluation = None
                
                # Use helper function to persist fallback analysis
                from services.system_design_service import SystemDesignService
                sd_service = SystemDesignService(db)
                _persist_system_design_analysis(
                    candidate_id=candidate_id,
                    final_report=fallback_report,
                    evaluation=fallback_evaluation,
                    db=db,
                    extract_strengths_fn=sd_service._extract_strengths_and_improvements_simple
                )
                logger.info(f"[DATA_SOURCE] ✅ Committed fallback system design analysis to POSTGRESQL for candidate {candidate_id}")
                
                # Mark analysis as completed (even with fallback)
                status_service.mark_completed(candidate_id, SectionType.SYSTEM_DESIGN)
                logger.info(f"[ANALYSIS_STATUS] ✅ Marked System Design analysis as COMPLETED (fallback) for candidate {candidate_id}")
                
                # Emit completion event
                from services.analysis_events import on_section_analysis_completed
                on_section_analysis_completed(candidate_id, SectionType.SYSTEM_DESIGN)
                return
        
        except Exception as e:
            # Outer exception handler for processing submitted record
            logger.error(f"Error processing submitted system design record for candidate {candidate_id}: {str(e)}", exc_info=True)
            raise

    except Exception as e:
        logger.error(f"Error analyzing system design for candidate {candidate_id}: {str(e)}", exc_info=True)
        db.rollback()
        
        # Mark analysis as failed
        try:
            status_service.mark_failed(candidate_id, SectionType.SYSTEM_DESIGN)
            logger.info(f"[ANALYSIS_STATUS] ❌ Marked System Design analysis as FAILED for candidate {candidate_id}")
        except Exception as status_error:
            logger.error(f"Failed to mark System Design analysis as failed: {str(status_error)}")
        
        raise


def analyze_final(candidate_id: str, db: Session) -> None:
    """
    Standalone final analysis function - idempotent and background-safe.
    
    This function:
    1. Checks if final analysis is already completed (idempotent)
    2. Aggregates scores from all section analyses
    3. Determines integrity level and pass/fail result
    4. Generates LLM summary of overall interview performance
    5. Persists final analysis results
    6. Marks final analysis status as COMPLETED
    
    This function is designed to be called from background jobs after all
    section analyses are completed. It is idempotent - safe to call multiple times.
    
    Args:
        candidate_id: UUID of the candidate
        db: Database session
    """
    from services.analysis_status_service import AnalysisStatusService
    from utils.analysis_summary import generate_interview_summary
    
    status_service = AnalysisStatusService(db)
    
    try:
        logger.info(f"[FINAL_ANALYSIS] Starting final analysis for candidate {candidate_id}")
        
        # Check if final analysis is already completed (idempotent check)
        final_record = status_service.get_status(candidate_id, SectionType.FINAL)
        if final_record and final_record.status == AnalysisStatus.COMPLETED.value:
            logger.info(f"[FINAL_ANALYSIS] ⏭️  Final analysis already completed for candidate {candidate_id}, skipping")
            return
        
        # Mark final analysis as in progress (atomic operation)
        try:
            status_service.mark_in_progress(candidate_id, SectionType.FINAL)
            logger.info(f"[ANALYSIS_STATUS] 🔄 Marked FINAL analysis as IN_PROGRESS for candidate {candidate_id}")
        except Exception as e:
            # If marking in progress fails (e.g., another job already started), exit gracefully
            logger.warning(f"[FINAL_ANALYSIS] Another job may have started final analysis: {str(e)}")
            return
        
        # Fetch interview analysis record
        logger.info(f"[DATA_SOURCE] 📊 Fetching interview analysis from POSTGRESQL for final analysis for candidate {candidate_id}")
        interview_analysis = db.query(InterviewAnalysisTable).filter(
            InterviewAnalysisTable.candidate_id == candidate_id
        ).first()
        
        if not interview_analysis:
            logger.warning(f"[DATA_SOURCE] ❌ No interview analysis found in POSTGRESQL for candidate {candidate_id}, creating new record")
            interview_analysis = InterviewAnalysisTable(candidate_id=candidate_id)
            db.add(interview_analysis)
            db.flush()
        
        logger.info(f"[DATA_SOURCE] ✅ Found interview analysis in POSTGRESQL for candidate {candidate_id}")
        
        # Extract section analyses
        mcq_analysis = interview_analysis.mcq_analysis or {}
        coding_analysis = interview_analysis.coding_analysis or {}
        system_design_analysis = interview_analysis.system_design_analysis or {}
        cheat_metrics = interview_analysis.cheat_metrics or {}
        
        # Extract metadata for summary generation
        mcq_metadata = {
            "score": mcq_analysis.get("score", 0),
            "attempted": mcq_analysis.get("attempted", {"easy": 0, "medium": 0, "hard": 0}),
            "correct": mcq_analysis.get("correct", {"easy": 0, "medium": 0, "hard": 0})
        }
        
        coding_metadata = {
            "total_score": coding_analysis.get("total_score", 0),
            "time_taken": coding_analysis.get("time_taken", 0),
            "total_submitted": coding_analysis.get("total_submitted", 0),
            "total_correct": coding_analysis.get("total_correct", 0),
            "partially_correct": coding_analysis.get("partially_correct", 0)
        }
        
        system_design_metadata = {
            "score": system_design_analysis.get("score", 0),
            "summary": system_design_analysis.get("summary", "N/A"),
            "key_strengths": system_design_analysis.get("key_strengths", []),
            "areas_of_improvement": system_design_analysis.get("things_to_improve", []),
            "time_taken": system_design_analysis.get("time_taken", 0)
        }
        
        integrity_metadata = {
            "tab_switch_count": cheat_metrics.get("tab_change", 0),
            "fullscreen_exits_count": cheat_metrics.get("full_screen_exits", 0),
            "multiple_faces": cheat_metrics.get("multiple_face", "no") == "yes"
        }
        
        # Generate summary using LLM
        logger.info(f"[FINAL_ANALYSIS] 🤖 Generating LLM summary for candidate {candidate_id}")
        summary = asyncio.run(generate_interview_summary(
            mcq_metadata=mcq_metadata,
            coding_metadata=coding_metadata,
            system_design_metadata=system_design_metadata,
            integrity_metadata=integrity_metadata
        ))
        logger.info(f"[FINAL_ANALYSIS] ✅ Generated LLM summary for candidate {candidate_id}")
        
        # Calculate overall score (average of MCQ, Coding, and System Design)
        mcq_score = mcq_metadata.get("score", 0)
        coding_score = coding_metadata.get("total_score", 0)
        system_design_score = system_design_metadata.get("score", 0)
        
        overall_percentage = round((mcq_score + coding_score + system_design_score) / 3)
        logger.info(f"[FINAL_ANALYSIS] 📊 Overall score: {overall_percentage}% (MCQ: {mcq_score}, Coding: {coding_score}, System Design: {system_design_score})")
        
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
            reason = "Low integrity"
        elif overall_percentage > 70:
            result = "PASS"
            reason = "High score"
        else:
            result = "FAIL"
            reason = "Low score"
        
        logger.info(f"[FINAL_ANALYSIS] ✅ Result: {result} ({reason}), Integrity: {'Low' if is_low_integrity else 'High'}")
        
        # Save final analysis results
        interview_analysis.overall_summary = summary
        interview_analysis.overall_percentage = overall_percentage
        interview_analysis.result = result
        db.commit()
        
        logger.info(f"[DATA_SOURCE] ✅ Saved final analysis to POSTGRESQL for candidate {candidate_id}")
        logger.info(f"[FINAL_ANALYSIS] ✅ Overall Score: {overall_percentage}%, Result: {result}")
        
        # Mark final analysis as completed
        status_service.mark_completed(candidate_id, SectionType.FINAL)
        logger.info(f"[ANALYSIS_STATUS] ✅ Marked FINAL analysis as COMPLETED for candidate {candidate_id}")
        
        # Trigger email sending after final analysis completes
        # Emails are sent asynchronously in background thread to avoid blocking
        try:
            from services.email_service import EmailService
            from models.candidate import Candidate
            from models.recruiter_admin_candidate import RecruiterAdminCandidate
            from models.recruiter_admin import RecruiterAdmin
            from models.job import Job
            from models.test_session import TestSession
            from core.config import settings
            import threading
            
            # Fetch candidate data (needed for emails)
            candidate = db.query(Candidate).filter(
                Candidate.candidate_id == candidate_id
            ).first()
            
            if candidate:
                def send_emails_after_final():
                    """Send emails after final analysis completes."""
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    from core.database import SessionLocal
                    email_db = SessionLocal()
                    try:
                        email_service = EmailService()
                        
                        # Get completion date from test_session (or use current time)
                        test_session = email_db.query(TestSession).filter(
                            TestSession.candidate_id == candidate_id
                        ).first()
                        completion_date = test_session.test_completed_at if test_session and test_session.test_completed_at else datetime.utcnow()
                        
                        # Step 1: Send candidate email
                        logger.info(f"[FINAL_ANALYSIS] Sending assessment report email to {candidate.email_id}")
                        loop.run_until_complete(
                            email_service.send_assessment_report_email(
                                candidate_id=candidate_id,
                                candidate_email=candidate.email_id,
                                candidate_name=candidate.name,
                                completion_date=completion_date,
                                db=email_db
                            )
                        )
                        logger.info(f"[FINAL_ANALYSIS] ✅ Assessment report email sent to {candidate.email_id}")
                        
                        # Step 2: Send recruiter email
                        assignment = email_db.query(RecruiterAdminCandidate).filter(
                            RecruiterAdminCandidate.candidate_id == candidate_id
                        ).first()
                        
                        if assignment:
                            recruiter = email_db.query(RecruiterAdmin).filter(
                                RecruiterAdmin.email_id == assignment.recruiter_admin_email
                            ).first()
                            
                            job = email_db.query(Job).filter(
                                Job.job_id == assignment.job_id
                            ).first()
                            
                            if recruiter and job:
                                # Get overall score (now available after analyze_final completes)
                                analysis = email_db.query(InterviewAnalysisTable).filter(
                                    InterviewAnalysisTable.candidate_id == candidate_id
                                ).first()
                                
                                overall_score = None
                                if analysis and analysis.overall_percentage is not None:
                                    overall_score = int(analysis.overall_percentage)
                                
                                # Build analysis report URL
                                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
                                candidate_ref = candidate.candidate_reference_number or candidate_id
                                analysis_report_url = f"{frontend_url}/admin/candidates/{candidate_ref}/interview-analysis"
                                
                                # Send recruiter email
                                logger.info(f"[FINAL_ANALYSIS] Sending test completion notification to recruiter {recruiter.email_id}")
                                email_sent = loop.run_until_complete(
                                    email_service.send_recruiter_test_completion_email(
                                        recruiter_email=recruiter.email_id,
                                        recruiter_name=recruiter.name,
                                        candidate_name=candidate.name,
                                        candidate_email=candidate.email_id,
                                        candidate_reference_number=candidate.candidate_reference_number,
                                        job_role=job.job_role,
                                        completion_date=completion_date,
                                        overall_score=overall_score,
                                        analysis_report_url=analysis_report_url
                                    )
                                )
                                
                                if email_sent:
                                    logger.info(f"[FINAL_ANALYSIS] ✅ Recruiter completion email sent to {recruiter.email_id}")
                                else:
                                    logger.warning(f"[FINAL_ANALYSIS] ⚠️ Recruiter completion email was not sent to {recruiter.email_id}")
                            else:
                                logger.warning(f"[FINAL_ANALYSIS] Recruiter or job not found for candidate {candidate_id}")
                        else:
                            logger.warning(f"[FINAL_ANALYSIS] No recruiter assignment found for candidate {candidate_id}")
                        
                    except Exception as email_error:
                        logger.error(f"Error sending emails after final analysis for candidate {candidate_id}: {str(email_error)}", exc_info=True)
                        # Don't raise - email sending failure shouldn't break final analysis
                    finally:
                        email_db.close()
                        try:
                            # Close all pending tasks before closing loop
                            pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                            if pending:
                                for task in pending:
                                    task.cancel()
                                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                        except Exception:
                            pass
                        finally:
                            loop.close()
                
                thread = threading.Thread(target=send_emails_after_final, daemon=True)
                thread.start()
                logger.info(f"[FINAL_ANALYSIS] ✅ Triggered email sending for candidate {candidate_id}")
            else:
                logger.warning(f"[FINAL_ANALYSIS] Candidate not found for email sending: {candidate_id}")
        except Exception as e:
            logger.warning(f"Failed to trigger email sending after final analysis for candidate {candidate_id}: {str(e)}")
            # Don't raise - email sending is non-critical
        
    except Exception as e:
        logger.error(f"Error in final analysis for candidate {candidate_id}: {str(e)}", exc_info=True)
        db.rollback()
        
        # Mark final analysis as failed
        try:
            status_service.mark_failed(candidate_id, SectionType.FINAL)
            logger.info(f"[ANALYSIS_STATUS] ❌ Marked FINAL analysis as FAILED for candidate {candidate_id}")
        except Exception as status_error:
            logger.error(f"Failed to mark FINAL analysis as failed: {str(status_error)}")
        
        raise

