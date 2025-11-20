"""
Recruiter Admin Candidate junction model for RECRUITER_ADMIN_CANDIDATE table.
"""
from sqlalchemy import Column, String, Date, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from core.database import Base


class RecruiterAdminCandidate(Base):
    """Recruiter Admin Candidate junction model."""
    
    __tablename__ = 'recruiter_admin_candidate'
    
    recruiter_admin_email = Column(
        String(255),
        ForeignKey('recruiter_admin.email_id'),
        nullable=False
    )
    candidate_id = Column(
        String(36),
        ForeignKey('candidate.candidate_id'),
        nullable=False
    )
    job_id = Column(
        String(36),
        ForeignKey('jobs.job_id'),
        nullable=False
    )
    assigned_at = Column(Date, nullable=False)
    
    # Composite primary key
    __table_args__ = (
        PrimaryKeyConstraint(
            'recruiter_admin_email',
            'candidate_id',
            'job_id'
        ),
    )
    
    # Relationships
    recruiter = relationship('RecruiterAdmin', back_populates='candidate_assignments')
    candidate = relationship('Candidate', back_populates='assignments')
    job = relationship('Job', back_populates='candidate_assignments')




