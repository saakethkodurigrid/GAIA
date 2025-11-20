"""
Recruiter Admin model for RECRUITER_ADMIN table.
"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class RecruiterAdmin(Base):
    """Recruiter Admin model representing RECRUITER_ADMIN table."""
    
    __tablename__ = 'recruiter_admin'
    
    email_id = Column(String(255), primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    role_id = Column(Integer, ForeignKey('role_table.role_id'), nullable=False)
    phone_number = Column(String(20), nullable=True)
    location = Column(String(255), nullable=True)
    
    # Relationships
    role = relationship('Role', backref='recruiters')
    jobs = relationship('Job', back_populates='recruiter')
    candidate_assignments = relationship('RecruiterAdminCandidate', back_populates='recruiter')




