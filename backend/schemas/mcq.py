"""
MCQ schemas for request and response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal


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
    total_score: int = Field(default=0, description="Total score (number of correct answers)")
    total_questions: int = Field(default=0, description="Total number of questions answered")
    correct_answers: int = Field(default=0, description="Number of correct answers")
    incorrect_answers: int = Field(default=0, description="Number of incorrect answers")


class GenerateMCQRequest(BaseModel):
    """Request schema for generating MCQ questions"""
    resume: str = Field(..., description="Candidate resume text", min_length=1)
    job_description: str = Field(..., description="Job description text", min_length=1)
    grade: Literal["T2", "T3"] = Field(default="T2", description="Grade level (T2 or T3)")


class MCQQuestion(BaseModel):
    """Schema for a single generated MCQ question"""
    question_id: str = Field(..., description="Question ID")
    question: str = Field(..., description="Question text")
    option1: str = Field(..., description="Option 1")
    option2: str = Field(..., description="Option 2")
    option3: str = Field(..., description="Option 3")
    option4: str = Field(..., description="Option 4")
    correct_option: int = Field(..., ge=1, le=4, description="Correct option number (1-4)")
    difficulty: Literal["easy", "medium", "hard"] = Field(..., description="Difficulty level")
    tags: List[str] = Field(default_factory=list, description="Question tags")


class MCQGenerationMetadata(BaseModel):
    """Metadata about generated questions"""
    total_questions: int = Field(..., description="Total number of questions generated")
    difficulty_distribution: Dict[str, int] = Field(..., description="Distribution of difficulty levels")
    domain: str = Field(..., description="Domain identified for the questions")
    subtopics_covered: List[str] = Field(default_factory=list, description="Subtopics covered")


class GenerateMCQResponse(BaseModel):
    """Response schema for MCQ question generation"""
    success: bool = Field(..., description="Whether generation was successful")
    message: str = Field(..., description="Response message")
    questions: List[MCQQuestion] = Field(default_factory=list, description="Generated questions")
    metadata: Optional[MCQGenerationMetadata] = Field(None, description="Generation metadata")


class InitializeRAGResponse(BaseModel):
    """Response schema for RAG initialization"""
    success: bool = Field(..., description="Whether initialization was successful")
    message: str = Field(..., description="Response message")

