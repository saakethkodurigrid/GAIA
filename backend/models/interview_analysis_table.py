"""
Interview Analysis Table model for INTERVIEW_ANALYSIS_TABLE table.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from core.database import Base


class InterviewAnalysisTable(Base):
    """Interview Analysis Table model representing INTERVIEW_ANALYSIS_TABLE table."""
    
    __tablename__ = 'interview_analysis_table'
    __table_args__ = (
        CheckConstraint("result IN ('PASS', 'FAIL')", name='check_result'),
    )
    
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id'), primary_key=True, nullable=False, index=True)
    mcq_analysis = Column(JSONB, nullable=True)
    coding_analysis = Column(JSONB, nullable=True)
    system_design_analysis = Column(JSONB, nullable=True)
    cheat_metrics = Column(JSONB, nullable=True)
    overall_percentage = Column(Integer, nullable=True)
    result = Column(String(10), nullable=True)
    overall_summary = Column(String, nullable=True)
    
    # Relationships
    candidate = relationship('Candidate', backref='interview_analysis')



