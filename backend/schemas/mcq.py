"""
MCQ schemas for request and response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional


class MCQQuestionResponse(BaseModel):
    """Response schema for a single MCQ question with options."""
    question_uuid: str = Field(..., description="UUID of the MCQ question")
    question: str = Field(..., description="The question text")
    options: List[str] = Field(..., description="List of answer options")


class MCQQuestionsResponse(BaseModel):
    """Response schema for listing MCQ questions."""
    success: bool
    message: str
    count: int
    questions: List[MCQQuestionResponse] = []


class MCQAnswerItem(BaseModel):
    """Schema for a single question-answer pair."""
    question_uuid: str = Field(..., description="UUID of the MCQ question", pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
    candidate_answer: str = Field(..., description="The candidate's selected answer", min_length=1)


class SaveMCQAnswerRequest(BaseModel):
    """Request schema for saving candidate answers to multiple MCQ questions."""
    answers: List[MCQAnswerItem] = Field(..., description="List of question-answer pairs", min_items=1)


class SaveMCQAnswerResponse(BaseModel):
    """Response schema for saving MCQ answers."""
    success: bool
    message: str
    saved_count: int = Field(..., description="Number of answers successfully saved")
    failed_count: int = Field(..., description="Number of answers that failed to save")
    failed_questions: List[str] = Field(default_factory=list, description="List of question UUIDs that failed to save")

