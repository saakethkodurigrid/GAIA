"""
Test Session schemas for request and response validation.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from schemas.mcq import SaveMCQAnswerRequest


class StartTestRequest(BaseModel):
    """Request schema for starting a test session."""
    duration_minutes: int = Field(default=180, ge=1, le=300, description="Test duration in minutes")


class StartTestResponse(BaseModel):
    """Response schema for starting a test session."""
    success: bool
    message: str
    test_start_time: Optional[datetime] = None
    remaining_seconds: int = Field(default=0, description="Remaining time in seconds")


class HeartbeatRequest(BaseModel):
    """Request schema for heartbeat."""
    client_timestamp: Optional[datetime] = Field(None, description="Client timestamp for sync")


class HeartbeatResponse(BaseModel):
    """Response schema for heartbeat."""
    success: bool
    message: str
    server_timestamp: datetime
    remaining_seconds: int = Field(default=0, description="Remaining time in seconds")


class CompleteTestRequest(BaseModel):
    """Request schema for completing a test session.
    
    Supports multiple completion methods: 'manual', 'tab_close', 'timer_expired', 
    'heartbeat_timeout' (reserved for future use), 'auto'.
    
    MCQ answers can be provided in two formats:
    1. Full format: SaveMCQAnswerRequest object (for regular API calls)
    2. Simplified format: List[Dict[str, str]] (for sendBeacon/tab close)
    3. Dict format: Dict with 'answers' key (serialized SaveMCQAnswerRequest)
    """
    completion_method: str = Field(
        default="manual",
        description="How test was completed: 'manual', 'tab_close', 'timer_expired', 'heartbeat_timeout' (reserved), 'auto'"
    )
    mcq_answers: Optional[Union[SaveMCQAnswerRequest, List[Dict[str, str]], Dict[str, Any]]] = Field(
        None, 
        description="MCQ answers - can be SaveMCQAnswerRequest object, List[Dict] for simplified format, or Dict with 'answers' key"
    )
    coding_answers: Optional[Dict[str, Any]] = Field(None, description="Coding answers (to be implemented)")
    system_design_data: Optional[Dict[str, Any]] = Field(None, description="System design data (to be implemented)")
    sections_completed: Optional[Dict[str, bool]] = Field(
        None,
        description="Sections completion status: {'mcq': true, 'coding': false, 'system_design': false}"
    )


class CompleteTestResponse(BaseModel):
    """Response schema for completing a test session."""
    success: bool
    message: str
    completed_at: Optional[datetime] = None


class TestStatusResponse(BaseModel):
    """Response schema for test status."""
    success: bool
    message: str
    status: Optional[str] = Field(None, description="Test status: 'active', 'completed', 'abandoned'")
    remaining_seconds: int = Field(default=0, description="Remaining time in seconds")
    sections_completed: Dict[str, bool] = Field(default_factory=dict, description="Sections completion status")
    last_activity: Optional[datetime] = None


class TabCloseCompletionRequest(BaseModel):
    """Request schema for tab close completion (optimized for sendBeacon)."""
    mcq_answers: Optional[List[Dict[str, str]]] = Field(None, description="MCQ answers in simplified format")
    coding_answers: Optional[Dict[str, Any]] = Field(None, description="Coding answers")
    system_design_data: Optional[Dict[str, Any]] = Field(None, description="System design data")
    sections_completed: Optional[Dict[str, bool]] = Field(None, description="Sections completion status")

