"""
Coding schemas for request and response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Literal, Any


class RunCodeRequest(BaseModel):
    """Request schema for running code."""
    question_id: str = Field(
        ..., 
        description="UUID of the coding question",
        pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    )
    language: Literal["python", "javascript", "java", "cpp", "csharp"] = Field(
        ..., 
        description="Programming language"
    )
    code: str = Field(..., description="Code to execute", min_length=1)
    mode: Literal["run", "run_all"] = Field(
        ..., 
        description="Execution mode: 'run' for sample test cases only, 'run_all' for all test cases"
    )


class RunCodeResponse(BaseModel):
    """Response schema for code execution results."""
    execution_id: Optional[str] = Field(None, description="Execution ID from execution service")
    summary: Dict[str, Any] = Field(..., description="Summary of test results")
    test_results: List[Dict[str, Any]] = Field(..., description="Detailed test results")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Execution metadata")
    timestamp: Optional[str] = Field(None, description="Execution timestamp")
    error: Optional[str] = Field(None, description="Error message if execution failed")


class SubmitCodingAnswerRequest(BaseModel):
    """Request schema for submitting coding question answer."""
    question_id: str = Field(
        ..., 
        description="UUID of the coding question",
        pattern=r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'
    )
    language: Literal["python", "javascript", "java", "cpp", "csharp"] = Field(
        ..., 
        description="Programming language"
    )
    code: str = Field(..., description="Final code submission", min_length=1)


class SubmitCodingAnswerResponse(BaseModel):
    """Response schema for coding answer submission."""
    success: bool = Field(..., description="Whether submission was successful")
    message: str = Field(..., description="Response message")
    question_id: str = Field(..., description="UUID of the coding question")
    score: int = Field(..., description="Total score achieved")
    test_cases_passed: int = Field(..., description="Number of test cases passed")
    total_test_cases: int = Field(..., description="Total number of test cases")
    sample_test_cases_passed: int = Field(..., description="Number of sample test cases passed")
    hidden_test_cases_passed: int = Field(..., description="Number of hidden test cases passed")
    execution_id: Optional[str] = Field(None, description="Execution ID from execution service")


class CodingQuestionResponse(BaseModel):
    """Response schema for a single coding question."""
    question_uuid: str = Field(..., description="UUID of the coding question")
    question: str = Field(..., description="The question text")
    sample_test_cases: List[Dict[str, Any]] = Field(default_factory=list, description="Sample test cases (visible to candidate)")
    boilerplate_code: Optional[str] = Field(None, description="Boilerplate code for the question")


class CodingQuestionsResponse(BaseModel):
    """Response schema for listing coding questions."""
    success: bool = Field(..., description="Whether the request was successful")
    message: str = Field(..., description="Response message")
    count: int = Field(..., description="Number of coding questions")
    questions: List[CodingQuestionResponse] = Field(default_factory=list, description="List of coding questions")

