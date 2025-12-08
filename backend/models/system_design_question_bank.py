"""
System Design Question Bank model for SYSTEM_DESIGN_QUESTION_BANK table.
"""
from sqlalchemy import Column, String, Text, Integer
from sqlalchemy.dialects.postgresql import JSONB
from core.database import Base


class SystemDesignQuestionBank(Base):
    """System Design Question Bank model representing SYSTEM_DESIGN_QUESTION_BANK table."""
    
    __tablename__ = 'system_design_question_bank'
    
    uuid = Column(String(36), primary_key=True, index=True)  # UUID as CHAR(36)
    question = Column(Text, nullable=False)
    evaluation_criteria = Column(Text, nullable=False)
    tags = Column(JSONB, nullable=True)
    
    # New columns for enhanced chat conversations
    domain = Column(String(50), nullable=True, index=True)  # e.g., 'hld', 'agentic-ai', 'distributed-systems'
    complexity = Column(String(20), nullable=True, index=True)  # e.g., 'easy', 'normal', 'hard'
    estimated_time_minutes = Column(Integer, nullable=True)  # Expected interview duration
    
    # Question-specific guidance for AI interviewer
    guidance_prompts = Column(JSONB, nullable=True, default={})  # Question-specific guidance by category
    expected_components = Column(JSONB, nullable=True, default=[])  # Key components that should appear
    common_pitfalls = Column(JSONB, nullable=True, default={})  # What candidates often miss
    hints = Column(JSONB, nullable=True, default={})  # Progressive hints for stuck candidates
    proactive_prompt_templates = Column(JSONB, nullable=True, default={})  # Templates for proactive prompts
    
    # Templates to guide candidates
    functional_requirements_template = Column(Text, nullable=True)  # Template for functional requirements
    non_functional_requirements_template = Column(Text, nullable=True)  # Template for non-functional requirements
    
    # Additional context for evaluator
    evaluation_context = Column(JSONB, nullable=True, default={})  # Domain-specific evaluation notes



