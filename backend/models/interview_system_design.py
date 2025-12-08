"""
Interview System Design model for INTERVIEW_SYSTEM_DESIGN table.
Consolidated table that stores assignment, session state, chat, and final results.
"""
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, CheckConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from core.database import Base


class InterviewSystemDesign(Base):
    """Interview System Design model representing INTERVIEW_SYSTEM_DESIGN table.
    
    This table consolidates:
    - Assignment metadata (candidate_id, question_uuid)
    - Session state (current_canvas, chat_messages, activity tracking)
    - Final results (score, diagram)
    """
    
    __tablename__ = 'interview_system_design'
    __table_args__ = (
        CheckConstraint("status IN ('assigned', 'in_progress', 'submitted', 'evaluated')", name='check_interview_system_design_status'),
        CheckConstraint("score IS NULL OR (score >= 0 AND score <= 100)", name='check_interview_system_design_score'),
        Index('idx_status', 'status'),
        Index('idx_submitted_at', 'submitted_at'),
        Index('idx_last_activity', 'last_activity_time'),
    )
    
    # Primary key
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id'), primary_key=True, nullable=False, index=True)
    question_uuid = Column(String(36), ForeignKey('system_design_question_bank.uuid'), primary_key=True, nullable=False, index=True)
    
    # Final results (populated on submit)
    score = Column(Integer, nullable=True)  # 0-100, calculated from evaluation
    diagram = Column(Text, nullable=True)  # Final submitted diagram (JSON string)
    
    # Session state (work-in-progress)
    current_canvas = Column(JSONB, nullable=True)  # Current canvas state (work-in-progress)
    previous_canvas = Column(JSONB, nullable=True)  # Previous canvas for change detection
    chat_messages = Column(JSONB, nullable=False, default=list)  # Array of {role, content, timestamp}
    
    # Activity tracking
    last_activity_time = Column(DateTime, nullable=True)
    last_drawing_activity_time = Column(DateTime, nullable=True)
    last_prompt_time = Column(DateTime, nullable=True)
    last_poll_time = Column(DateTime, nullable=True)
    prompt_history = Column(JSONB, nullable=False, default=list)  # List of prompt keys
    milestones = Column(JSONB, nullable=False, default=dict)  # Dict of milestone flags
    last_canvas_hash = Column(String(64), nullable=True)  # Hash for change detection
    
    # Timestamps
    created_at = Column(DateTime, nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(DateTime, nullable=False, server_default='CURRENT_TIMESTAMP', onupdate='CURRENT_TIMESTAMP')
    submitted_at = Column(DateTime, nullable=True)  # When solution was submitted
    
    # Status tracking
    status = Column(String(20), nullable=False, default='assigned', index=True)  # assigned, in_progress, submitted, evaluated
    
    # Relationships
    candidate = relationship('Candidate', backref='interview_system_designs')
    question = relationship('SystemDesignQuestionBank', backref='interview_system_designs')



