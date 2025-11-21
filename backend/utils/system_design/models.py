"""
Data models for the System Design Interview Platform
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime


class CanvasVersion(BaseModel):
    version: int
    data: Dict[str, Any]
    components: int
    edges: int
    timestamp: Optional[str] = None


class ChatMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    timestamp: Optional[str] = None


class Evaluation(BaseModel):
    version: int
    scores: Dict[str, float]  # {"architecture": 3.5, "scalability": 2.0, ...}
    feedback: str
    follow_up: Optional[str] = None


class Session(BaseModel):
    session_id: str
    candidate_id: str  # Candidate who owns this session
    question_id: str
    question_text: str
    canvas_versions: List[CanvasVersion]
    chat_history: List[ChatMessage]
    evaluations: List[Evaluation]
    current_canvas: Optional[Dict[str, Any]] = None  # Latest canvas state (may not be saved)
    previous_canvas: Optional[Dict[str, Any]] = None  # Previous canvas state for change detection
    last_activity_time: Optional[float] = None  # Unix timestamp of last activity (canvas or chat)
    last_drawing_activity_time: Optional[float] = None  # Unix timestamp of last significant drawing change
    last_prompt_time: Optional[float] = None  # Unix timestamp of last proactive prompt
    last_poll_time: Optional[float] = None  # Unix timestamp of last poll check
    prompt_history: List[str] = []  # Track what prompts have been sent to avoid duplicates
    milestones: Dict[str, bool] = {}  # Track progression: {"architecture_complete": False, "scaling_discussed": False, ...}
    last_canvas_hash: Optional[str] = None  # Hash of canvas for quick change detection
    created_at: Optional[str] = None
    ended_at: Optional[str] = None

