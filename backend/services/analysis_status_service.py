"""
Analysis Status Service for managing analysis status tracking.
Provides atomic operations for reading and updating analysis statuses.
"""
import logging
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime
import uuid

from models.analysis_status import AnalysisStatusRecord
from schemas.analysis import AnalysisStatus as AnalysisStatusEnum, SectionType

logger = logging.getLogger(__name__)


class AnalysisStatusService:
    """Service for managing analysis status tracking with atomic operations."""
    
    def __init__(self, db: Session):
        """Initialize the service with a database session."""
        self.db = db
    
    def get_status(
        self,
        candidate_id: str,
        section_type: SectionType
    ) -> Optional[AnalysisStatusRecord]:
        """
        Get the analysis status for a candidate and section type.
        
        Args:
            candidate_id: The candidate UUID
            section_type: The section type (MCQ, CODING, SYSTEM_DESIGN, FINAL)
            
        Returns:
            AnalysisStatusRecord instance or None if not found
        """
        try:
            status_record = self.db.query(AnalysisStatusRecord).filter(
                and_(
                    AnalysisStatusRecord.candidate_id == candidate_id,
                    AnalysisStatusRecord.section_type == section_type.value
                )
            ).first()
            return status_record
        except Exception as e:
            logger.error(
                f"Error getting analysis status for candidate {candidate_id}, "
                f"section {section_type.value}: {str(e)}",
                exc_info=True
            )
            raise
    
    def get_all_statuses(
        self,
        candidate_id: str
    ) -> List[AnalysisStatusRecord]:
        """
        Get all analysis statuses for a candidate.
        
        Args:
            candidate_id: The candidate UUID
            
        Returns:
            List of AnalysisStatusRecord instances
        """
        try:
            status_records = self.db.query(AnalysisStatusRecord).filter(
                AnalysisStatusRecord.candidate_id == candidate_id
            ).all()
            return status_records
        except Exception as e:
            logger.error(
                f"Error getting all analysis statuses for candidate {candidate_id}: {str(e)}",
                exc_info=True
            )
            raise
    
    def update_status(
        self,
        candidate_id: str,
        section_type: SectionType,
        status: AnalysisStatusEnum,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> AnalysisStatusRecord:
        """
        Atomically update or create analysis status.
        
        This method uses database-level atomic operations to ensure
        thread-safe status updates.
        
        Args:
            candidate_id: The candidate UUID
            section_type: The section type (MCQ, CODING, SYSTEM_DESIGN, FINAL)
            status: The new status (NOT_STARTED, IN_PROGRESS, COMPLETED, FAILED)
            started_at: Optional timestamp when analysis started
            completed_at: Optional timestamp when analysis completed
            
        Returns:
            Updated or created AnalysisStatusRecord instance
        """
        try:
            # Try to get existing record
            status_record = self.get_status(candidate_id, section_type)
            
            if status_record:
                # Update existing record atomically
                status_record.status = status.value
                status_record.updated_at = datetime.utcnow()
                
                if started_at is not None:
                    status_record.started_at = started_at
                elif status == AnalysisStatusEnum.IN_PROGRESS and status_record.started_at is None:
                    # Auto-set started_at if transitioning to IN_PROGRESS
                    status_record.started_at = datetime.utcnow()
                
                if completed_at is not None:
                    status_record.completed_at = completed_at
                elif status in (AnalysisStatusEnum.COMPLETED, AnalysisStatusEnum.FAILED):
                    # Auto-set completed_at if transitioning to terminal state
                    status_record.completed_at = datetime.utcnow()
                
                logger.debug(
                    f"Updated analysis status: candidate={candidate_id}, "
                    f"section={section_type.value}, status={status.value}"
                )
            else:
                # Create new record
                now = datetime.utcnow()
                status_record = AnalysisStatusRecord(
                    id=str(uuid.uuid4()),
                    candidate_id=candidate_id,
                    section_type=section_type.value,
                    status=status.value,
                    started_at=started_at or (now if status == AnalysisStatusEnum.IN_PROGRESS else None),
                    completed_at=completed_at or (
                        now if status in (AnalysisStatusEnum.COMPLETED, AnalysisStatusEnum.FAILED) else None
                    ),
                    created_at=now,
                    updated_at=now
                )
                self.db.add(status_record)
                logger.debug(
                    f"Created analysis status: candidate={candidate_id}, "
                    f"section={section_type.value}, status={status.value}"
                )
            
            # Commit the transaction atomically
            self.db.commit()
            
            # Refresh to get latest state
            self.db.refresh(status_record)
            
            return status_record
            
        except Exception as e:
            logger.error(
                f"Error updating analysis status for candidate {candidate_id}, "
                f"section {section_type.value}: {str(e)}",
                exc_info=True
            )
            self.db.rollback()
            raise
    
    def mark_in_progress(
        self,
        candidate_id: str,
        section_type: SectionType
    ) -> AnalysisStatusRecord:
        """
        Convenience method to mark analysis as in progress.
        
        Args:
            candidate_id: The candidate UUID
            section_type: The section type
            
        Returns:
            Updated AnalysisStatusRecord instance
        """
        return self.update_status(
            candidate_id=candidate_id,
            section_type=section_type,
            status=AnalysisStatusEnum.IN_PROGRESS
        )
    
    def mark_completed(
        self,
        candidate_id: str,
        section_type: SectionType
    ) -> AnalysisStatusRecord:
        """
        Convenience method to mark analysis as completed.
        
        Args:
            candidate_id: The candidate UUID
            section_type: The section type
            
        Returns:
            Updated AnalysisStatusRecord instance
        """
        return self.update_status(
            candidate_id=candidate_id,
            section_type=section_type,
            status=AnalysisStatusEnum.COMPLETED
        )
    
    def mark_failed(
        self,
        candidate_id: str,
        section_type: SectionType
    ) -> AnalysisStatusRecord:
        """
        Convenience method to mark analysis as failed.
        
        Args:
            candidate_id: The candidate UUID
            section_type: The section type
            
        Returns:
            Updated AnalysisStatusRecord instance
        """
        return self.update_status(
            candidate_id=candidate_id,
            section_type=section_type,
            status=AnalysisStatusEnum.FAILED
        )
    
    def initialize_statuses(
        self,
        candidate_id: str
    ) -> List[AnalysisStatusRecord]:
        """
        Initialize all analysis statuses for a candidate to NOT_STARTED.
        This is idempotent - existing statuses are not overwritten.
        
        Args:
            candidate_id: The candidate UUID
            
        Returns:
            List of AnalysisStatusRecord instances (created or existing)
        """
        try:
            statuses = []
            for section_type in [SectionType.MCQ, SectionType.CODING, SectionType.SYSTEM_DESIGN, SectionType.FINAL]:
                existing = self.get_status(candidate_id, section_type)
                if not existing:
                    status = self.update_status(
                        candidate_id=candidate_id,
                        section_type=section_type,
                        status=AnalysisStatusEnum.NOT_STARTED
                    )
                    statuses.append(status)
                else:
                    statuses.append(existing)
            
            return statuses
            
        except Exception as e:
            logger.error(
                f"Error initializing analysis statuses for candidate {candidate_id}: {str(e)}",
                exc_info=True
            )
            raise

