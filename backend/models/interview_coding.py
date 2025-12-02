"""
Interview Coding model for INTERVIEW_CODING table.
"""
from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class InterviewCoding(Base):
    """Interview Coding model representing INTERVIEW_CODING table."""
    
    __tablename__ = 'interview_coding'
    
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id'), primary_key=True, nullable=False, index=True)
    question_uuid = Column(String(36), ForeignKey('coding_question_bank.uuid'), primary_key=True, nullable=False, index=True)
    score = Column(Integer, nullable=True)
    test_cases_passed = Column(Integer, nullable=True)
    difficulty = Column(String(50), nullable=True)
    
    # Relationships
    candidate = relationship('Candidate', backref='interview_codings')
    question = relationship('CodingQuestionBank', backref='interview_codings')



