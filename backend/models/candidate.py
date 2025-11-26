"""
Candidate model for CANDIDATE table.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, Text, CheckConstraint, Numeric
from sqlalchemy.orm import relationship
from core.database import Base


class Candidate(Base):
    """Candidate model representing CANDIDATE table."""
    
    __tablename__ = 'candidate'
    __table_args__ = (
        CheckConstraint("status IN ('shortlisted', 'rejected', 'scheduled', 'in progress', 'completed', 'selected', 'not selected')", name='candidate_status_check'),
    )
    
    candidate_id = Column(String(36), primary_key=True, index=True)  # UUID as CHAR(36)
    name = Column(String(255), nullable=False)
    email_id = Column(String(255), nullable=False, index=True)
    resume = Column(Text, nullable=True)
    resume_score = Column(Numeric, nullable=True)  # Resume score (0-100), matches DB numeric type
    role_id = Column(Integer, ForeignKey('role_table.role_id'), nullable=False)
    phone_number = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    status = Column(String(20), nullable=False)
    scheduled_date = Column(DateTime, nullable=True)
    
    # Relationships
    role = relationship('Role', backref='candidates')
    assignments = relationship('RecruiterAdminCandidate', back_populates='candidate')

