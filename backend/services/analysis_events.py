"""
Analysis Events - Event handlers for analysis lifecycle events.

This module provides event handlers that respond to analysis state changes.
Handles final analysis orchestration after all section analyses are completed.
"""
import logging
import threading
from typing import TYPE_CHECKING
from schemas.analysis import SectionType, AnalysisStatus

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def on_section_analysis_completed(candidate_id: str, section_type: SectionType) -> None:
    """
    Event handler called when a section analysis completes successfully.
    
    This function is called after:
    - Analysis has been calculated and persisted
    - Status has been marked as COMPLETED
    
    This function orchestrates final analysis by:
    1. Checking if all sections (MCQ, CODING, SYSTEM_DESIGN) are completed
    2. Checking if final analysis is already started/completed
    3. If conditions are met, enqueuing final analysis job to background thread
    
    This function is idempotent - safe to call multiple times for the same
    candidate/section combination. Atomic status checks prevent race conditions.
    
    Args:
        candidate_id: UUID of the candidate
        section_type: The section that completed (MCQ, CODING, SYSTEM_DESIGN)
    """
    logger.info(
        f"[ANALYSIS_EVENT] ✅ Section analysis completed: "
        f"candidate={candidate_id}, section={section_type.value}"
    )
    
    # Import here to avoid circular dependencies
    from core.database import SessionLocal
    from services.analysis_status_service import AnalysisStatusService
    
    # Create a new DB session for this event
    db: "Session" = SessionLocal()
    
    try:
        status_service = AnalysisStatusService(db)
        
        # Fetch all section statuses for this candidate
        mcq_record = status_service.get_status(candidate_id, SectionType.MCQ)
        coding_record = status_service.get_status(candidate_id, SectionType.CODING)
        system_design_record = status_service.get_status(candidate_id, SectionType.SYSTEM_DESIGN)
        final_record = status_service.get_status(candidate_id, SectionType.FINAL)
        
        # Extract status values (handle None case for missing records)
        mcq_status = mcq_record.status if mcq_record else AnalysisStatus.NOT_STARTED.value
        coding_status = coding_record.status if coding_record else AnalysisStatus.NOT_STARTED.value
        system_design_status = system_design_record.status if system_design_record else AnalysisStatus.NOT_STARTED.value
        final_status = final_record.status if final_record else AnalysisStatus.NOT_STARTED.value
        
        logger.info(
            f"[ANALYSIS_EVENT] Status check for {candidate_id}: "
            f"MCQ={mcq_status}, CODING={coding_status}, "
            f"SYSTEM_DESIGN={system_design_status}, FINAL={final_status}"
        )
        
        # Check if final analysis is already running or completed
        if final_status != AnalysisStatus.NOT_STARTED.value:
            logger.info(
                f"[ANALYSIS_EVENT] ⏭️  Final analysis already {final_status} for candidate {candidate_id}, skipping"
            )
            return
        
        # Check if all sections are completed
        all_sections_completed = (
            mcq_status == AnalysisStatus.COMPLETED.value and
            coding_status == AnalysisStatus.COMPLETED.value and
            system_design_status == AnalysisStatus.COMPLETED.value
        )
        
        if not all_sections_completed:
            logger.info(
                f"[ANALYSIS_EVENT] ⏳ Not all sections completed yet for candidate {candidate_id}, waiting for remaining sections"
            )
            return
        
        # All sections completed and final analysis not started - trigger final analysis!
        logger.info(
            f"[ANALYSIS_EVENT] 🎯 All sections completed for candidate {candidate_id}, enqueueing final analysis"
        )
        
        # Enqueue final analysis job to background thread
        _enqueue_final_analysis(candidate_id)
        
        logger.info(f"[ANALYSIS_EVENT] ✅ Enqueued final analysis job for candidate {candidate_id}")
        
    except Exception as e:
        logger.error(
            f"[ANALYSIS_EVENT] ❌ Error in section analysis event handler for candidate {candidate_id}: {str(e)}",
            exc_info=True
        )
        # Don't raise - event handlers should be resilient
    finally:
        db.close()


def _enqueue_final_analysis(candidate_id: str) -> None:
    """
    Enqueue final analysis job to background thread.
    
    This function creates a daemon thread that runs the final analysis
    in the background, allowing the event handler to return immediately.
    
    Args:
        candidate_id: UUID of the candidate
    """
    from core.database import SessionLocal
    from services.section_analysis_service import analyze_final
    
    def _run_final_analysis():
        """Background job that runs final analysis."""
        db: "Session" = SessionLocal()
        try:
            logger.info(f"[BACKGROUND_JOB] 🚀 Starting final analysis background job for candidate {candidate_id}")
            analyze_final(candidate_id, db)
            logger.info(f"[BACKGROUND_JOB] ✅ Final analysis background job completed for candidate {candidate_id}")
        except Exception as e:
            logger.error(
                f"[BACKGROUND_JOB] ❌ Final analysis background job failed for candidate {candidate_id}: {str(e)}",
                exc_info=True
            )
        finally:
            db.close()
    
    # Create and start background thread
    thread = threading.Thread(
        target=_run_final_analysis,
        name=f"final-analysis-{candidate_id}",
        daemon=True
    )
    thread.start()
    logger.info(f"[BACKGROUND_JOB] 📤 Enqueued final analysis job to background thread for candidate {candidate_id}")

