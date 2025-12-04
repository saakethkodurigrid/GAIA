"""
Test Session model for TEST_SESSION table.
Tracks active test sessions, timing, and completion status for candidates.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from core.database import Base


class TestSession(Base):
    """Test Session model representing TEST_SESSION table."""
    
    __tablename__ = 'test_session'
    __table_args__ = (
        CheckConstraint("status IN ('active', 'completed', 'abandoned')", name='test_session_status_check'),
        CheckConstraint("completion_method IN ('manual', 'tab_close', 'timer_expired', 'heartbeat_timeout', 'auto') OR completion_method IS NULL", name='test_session_completion_method_check'),
    )
    
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id'), primary_key=True, index=True, nullable=False)
    test_start_time = Column(DateTime, nullable=False)
    test_duration_minutes = Column(Integer, nullable=False, default=60)
    last_heartbeat = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    status = Column(String(20), nullable=False, default='active')
    completion_method = Column(String(50), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    sections_completed = Column(JSONB, nullable=True)  # {"mcq": true, "coding": false, "system_design": false}
    pending_answers = Column(JSONB, nullable=True)  # Temporary storage for unsaved answers
    created_at = Column(DateTime, nullable=False, server_default='CURRENT_TIMESTAMP')
    updated_at = Column(DateTime, nullable=False, server_default='CURRENT_TIMESTAMP', onupdate='CURRENT_TIMESTAMP')
    
    # Relationships
    candidate = relationship('Candidate', backref='test_session')

