"""
Interview System Design model for INTERVIEW_SYSTEM_DESIGN table.
"""
from sqlalchemy import Column, String, Integer, Text, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base


class InterviewSystemDesign(Base):
    """Interview System Design model representing INTERVIEW_SYSTEM_DESIGN table."""
    
    __tablename__ = 'interview_system_design'
    
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id'), primary_key=True, nullable=False, index=True)
    question_uuid = Column(String(36), ForeignKey('system_design_question_bank.uuid'), primary_key=True, nullable=False, index=True)
    score = Column(Integer, nullable=True)
    diagram = Column(Text, nullable=True)
    
    # Relationships
    candidate = relationship('Candidate', backref='interview_system_designs')
    question = relationship('SystemDesignQuestionBank', backref='interview_system_designs')



