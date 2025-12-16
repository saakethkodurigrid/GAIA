"""
Candidate schemas for request and response validation.
"""
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class ScheduleTestRequest(BaseModel):
    """Request schema for scheduling a test."""
    scheduled_date: datetime = Field(..., description="Date and time for the test in ISO format")


class ScheduleTestResponse(BaseModel):
    """Response schema for scheduling a test."""
    success: bool
    message: str
    scheduled_date: Optional[str] = None  # ISO format datetime string


class GetScheduledDateResponse(BaseModel):
    """Response schema for getting scheduled date."""
    success: bool
    message: str
    scheduled_date: Optional[str] = None  # ISO format datetime string with timezone


class InterviewSummaryResponse(BaseModel):
    """Response schema for interview summary with candidate details."""
    success: bool
    message: str
    candidate: dict = Field(..., description="Candidate details")
    summary: Optional[str] = Field(None, description="Overall interview summary (4-line LLM-generated summary)")
    mcq_analysis: Optional[dict] = Field(None, description="MCQ analysis data")
    coding_analysis: Optional[dict] = Field(None, description="Coding analysis data")
    system_design_analysis: Optional[dict] = Field(None, description="System design analysis data")
    cheat_metrics: Optional[dict] = Field(None, description="Integrity/cheat metrics")
    section_timings: Optional[dict] = Field(None, description="Section time taken in seconds: {'mcq': 1530, 'coding': 2970, 'system_design': 2700}")

