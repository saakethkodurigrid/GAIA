"""
System Design schemas for request and response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class CanvasData(BaseModel):
    """Schema for Excalidraw canvas data."""
    elements: List[Dict[str, Any]]
    appState: Optional[Dict[str, Any]] = None
    files: Optional[Dict[str, Any]] = None


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""
    message: str = Field(..., description="The chat message content", min_length=1)
    session_id: str = Field(..., description="Session ID for the interview")
    
    class Config:
        extra = "forbid"


class CanvasUpdateRequest(BaseModel):
    """Request schema for canvas updates."""
    session_id: str = Field(..., description="Session ID for the interview")
    canvas_data: CanvasData = Field(..., description="Canvas data from Excalidraw")
    action: str = Field(..., description="Action type: 'save', 'submit', or 'update'")
    change_hash: Optional[str] = Field(None, description="Hash of canvas changes for optimization")


class SessionCreateRequest(BaseModel):
    """Request schema for creating a new interview session."""
    question_id: Optional[str] = Field(None, description="Question ID (legacy)")
    question_text: Optional[str] = Field(None, description="Question text (if custom)")
    question_uuid: Optional[str] = Field(None, description="UUID from SYSTEM_DESIGN_QUESTION_BANK")
    tag: Optional[str] = Field(None, description="Tag for random question selection (e.g., 'normal_hld', 'agentic_ai_hld')")
    candidate_id: Optional[str] = Field(None, description="Candidate ID (auto-filled from auth if not provided)")


class SessionResponse(BaseModel):
    """Response schema for session creation."""
    session_id: str
    question_text: str
    question_uuid: Optional[str] = None


class QuestionResponse(BaseModel):
    """Response schema for a single question."""
    uuid: str
    question_id: str
    question: str
    evaluation_criteria: str
    tags: Optional[Dict[str, Any]] = None


class QuestionsResponse(BaseModel):
    """Response schema for listing questions."""
    questions: List[QuestionResponse]


class ChatMessageResponse(BaseModel):
    """Response schema for chat message."""
    user_message: Dict[str, Any]
    ai_response: Optional[str] = None
    evaluation: Optional[Dict[str, Any]] = None


class CanvasUpdateResponse(BaseModel):
    """Response schema for canvas update."""
    status: str
    version: Optional[int] = None
    evaluation: Optional[Dict[str, Any]] = None
    evaluation_message: Optional[str] = None


class ProactivePromptResponse(BaseModel):
    """Response schema for proactive prompt check."""
    has_prompt: bool
    prompt: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Response schema for chat history."""
    messages: List[Dict[str, Any]]


class FinalReportResponse(BaseModel):
    """Response schema for final evaluation report."""
    session_id: str
    question: str
    average_scores: Dict[str, float]
    timeline: List[Dict[str, Any]]
    total_versions: int
    total_messages: int
    lowest_area: Optional[str] = None
    suggested_learning: List[str]

