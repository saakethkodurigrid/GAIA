"""
Test session model for TEST_SESSION table.
"""
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref
from core.database import Base


class TestSession(Base):
    """Test session model - one-to-one with Candidate."""
    
    __tablename__ = 'test_session'
    
    candidate_id = Column(String(36), ForeignKey('candidate.candidate_id'), primary_key=True)
    test_start_time = Column(DateTime, nullable=True)
    test_duration_minutes = Column(Integer, nullable=True, default=180)
    last_heartbeat = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=True)
    completion_method = Column(String(50), nullable=True)
    test_completed_at = Column(DateTime, nullable=True)
    sections_completed = Column(JSONB, nullable=True)  # {"mcq": true, "coding": false, "system_design": false}
    pending_answers = Column(JSONB, nullable=True)  # Temporary storage for unsaved answers
    section_timings = Column(JSONB, nullable=True)  # {"mcq": {"started_at": "...", "completed_at": "...", "duration_seconds": 1530}, ...}
    
    # Relationship - one-to-one with Candidate
    # uselist=False in backref ensures candidate.test_session returns a single object, not a list
    candidate = relationship('Candidate', backref=backref('test_session', uselist=False))

