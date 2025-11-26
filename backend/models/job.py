"""
Job model for JOBS table.
"""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class Job(Base):
    """Job model representing JOBS table."""
    
    __tablename__ = 'jobs'
    
    job_id = Column(String(36), primary_key=True, index=True)  # UUID as CHAR(36)
    job_description = Column(Text, nullable=False)
    job_role = Column(Text, nullable=False)  # Changed from String(255) to Text for unlimited length
    recruiter_email_id = Column(
        String(255),
        ForeignKey('recruiter_admin.email_id'),
        nullable=False
    )
    grade = Column(String(10), nullable=False)  # Grade level (e.g., T1, T2, T3, etc.)
    
    # Relationships
    recruiter = relationship('RecruiterAdmin', back_populates='jobs')
    candidate_assignments = relationship('RecruiterAdminCandidate', back_populates='job')


