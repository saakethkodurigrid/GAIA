"""
Interview MCQ model for INTERVIEW_MCQ table.
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from core.database import Base


class InterviewMCQ(Base):
    """Interview MCQ model representing INTERVIEW_MCQ table."""
    
    __tablename__ = 'interview_mcq'
    
    uuid = Column(String(36), primary_key=True, index=True)  # UUID as CHAR(36)
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id'), nullable=False, index=True)
    question = Column(Text, nullable=False)
    correct_answer = Column(Text, nullable=False)
    candidate_answer = Column(Text, nullable=True)
    score = Column(Integer, nullable=True)
    tags = Column(JSONB, nullable=True)
    difficulty = Column(String(50), nullable=True)
    
    # Relationships
    candidate = relationship('Candidate', backref='interview_mcqs')



