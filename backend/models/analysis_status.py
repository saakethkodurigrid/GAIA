"""
Analysis Status model for tracking analysis execution status.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, CheckConstraint, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime


class AnalysisStatusRecord(Base):
    """Analysis Status Record model for tracking analysis execution status.
    
    Tracks the status of section analysis (MCQ, CODING, SYSTEM_DESIGN) 
    and final analysis for each candidate.
    """
    
    __tablename__ = 'analysis_status'
    __table_args__ = (
        CheckConstraint(
            "status IN ('not_started', 'in_progress', 'completed', 'failed')",
            name='check_analysis_status'
        ),
        CheckConstraint(
            "section_type IN ('MCQ', 'CODING', 'SYSTEM_DESIGN', 'FINAL')",
            name='check_section_type'
        ),
        UniqueConstraint('candidate_id', 'section_type', name='uq_candidate_section'),
        Index('idx_candidate_id', 'candidate_id'),
        Index('idx_section_type', 'section_type'),
        Index('idx_status', 'status'),
        Index('idx_candidate_section', 'candidate_id', 'section_type'),
    )
    
    id = Column(String(36), primary_key=True)  # UUID as primary key
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id', ondelete='CASCADE'), nullable=False, index=True)
    section_type = Column(String(20), nullable=False, index=True)  # MCQ, CODING, SYSTEM_DESIGN, FINAL
    status = Column(String(20), nullable=False, index=True)  # not_started, in_progress, completed, failed
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    candidate = relationship('Candidate', backref='analysis_statuses')

