"""
System Design Question Bank model for SYSTEM_DESIGN_QUESTION_BANK table.
"""
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from core.database import Base


class SystemDesignQuestionBank(Base):
    """System Design Question Bank model representing SYSTEM_DESIGN_QUESTION_BANK table."""
    
    __tablename__ = 'system_design_question_bank'
    
    uuid = Column(String(36), primary_key=True, index=True)  # UUID as CHAR(36)
    question = Column(Text, nullable=False)
    evaluation_criteria = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=True)



