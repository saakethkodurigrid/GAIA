"""
Coding Question Bank model for CODING_QUESTION_BANK table.
"""
from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from core.database import Base


class CodingQuestionBank(Base):
    """Coding Question Bank model representing CODING_QUESTION_BANK table."""
    
    __tablename__ = 'coding_question_bank'
    
    uuid = Column(String(36), primary_key=True, index=True)  # UUID as CHAR(36)
    question = Column(Text, nullable=False)
    sample_test_cases = Column(JSONB, nullable=False)
    test_cases = Column(JSONB, nullable=False)
    boiler_plate = Column(Text, nullable=True)
    difficulty = Column(String(50), nullable=True)
    tags = Column(JSONB, nullable=True)



