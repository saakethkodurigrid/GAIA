"""
Pydantic Models for API Request/Response
"""
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class Question(BaseModel):
    """Question model matching questions.json structure"""
    question_id: str
    question: str
    option1: str
    option2: str
    option3: str
    option4: str
    correct_option: int = Field(..., ge=1, le=4)
    difficulty: Literal["easy", "medium", "hard"]
    tags: List[str]


class QuestionRequest(BaseModel):
    """Request model for question generation"""
    resume: str = Field(..., description="Candidate resume text")
    job_description: str = Field(..., description="Job description text")
    grade: Literal["T2", "T3"] = Field(..., description="Grade level (T2 or T3)")


class QuestionMetadata(BaseModel):
    """Metadata about generated questions"""
    total_questions: int
    difficulty_distribution: dict
    domain: str
    subtopics_covered: List[str]


class QuestionResponse(BaseModel):
    """Response model for question generation"""
    questions: List[Question]
    metadata: Optional[QuestionMetadata] = None


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    rag_initialized: bool

