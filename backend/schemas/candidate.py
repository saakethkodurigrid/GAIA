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

